import uuid
from collections import deque
from enum import Enum
from typing import Dict, List, Set, Union

import marshmallow as ma
from flask import Response, g, jsonify, request
from marshmallow import Schema as MarshmallowSchema
from marshmallow import fields as f
from sqlalchemy import or_
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.db import db
from ereuse_devicehub.inventory.models import Transfer
from ereuse_devicehub.query import things_response
from ereuse_devicehub.resources.action.models import Confirm, Revoke, Trade
from ereuse_devicehub.resources.device.models import Computer, DataStorage, Device
from ereuse_devicehub.resources.lot.models import Lot, Path
from ereuse_devicehub.teal.marshmallow import EnumField
from ereuse_devicehub.teal.resource import View


class LotFormat(Enum):
    UiTree = 'UiTree'


class LotView(View):
    class FindArgs(MarshmallowSchema):
        """Allowed arguments for the ``find``
        method (GET collection) endpoint
        """

        format = EnumField(LotFormat, missing=None)
        search = f.Str(missing=None)
        type = f.Str(missing=None)

    def post(self):
        l = request.get_json()
        lot = Lot(**l)
        db.session.add(lot)
        db.session().final_flush()
        ret = self.schema.jsonify(lot)
        ret.status_code = 201
        db.session.commit()
        return ret

    def patch(self, id):
        patch_schema = self.resource_def.SCHEMA(
            only=(
                'name',
                'description',
                'transfer_state',
                'receiver_address',
                'amount',
                'devices',
                'owner_address',
            ),
            partial=True,
        )
        l = request.get_json(schema=patch_schema)
        lot = Lot.query.filter_by(id=id).one()
        device_fields = [
            'transfer_state',
            'receiver_address',
            'amount',
            'owner_address',
        ]
        computers = [x for x in lot.all_devices if isinstance(x, Computer)]
        for key, value in l.items():
            setattr(lot, key, value)
            if key in device_fields:
                for dev in computers:
                    setattr(dev, key, value)
        db.session.commit()
        return Response(status=204)

    def one(self, id: uuid.UUID):
        """Gets one action."""
        lot = Lot.query.filter_by(id=id).one()  # type: Lot
        return self.schema.jsonify(lot, nested=2)

    # @ereuse_devicehub.teal.cache.cache(datetime.timedelta(minutes=5))
    def find(self, args: dict):
        """Gets lots.

        By passing the value `UiTree` in the parameter `format`
        of the query you get a recursive nested suited for ui-tree::

             [
                {title: 'lot1',
                nodes: [{title: 'child1', nodes:[]}]
            ]

        Note that in this format filters are ignored.

        Otherwise it just returns the standard flat view of lots that
        you can filter.
        """
        if args['format'] == LotFormat.UiTree:
            lots = self.schema.dump(Lot.query, many=True, nested=2)
            ret = {
                'items': {l['id']: l for l in lots},
                'tree': self.ui_tree(),
                'url': request.path,
            }
        else:
            query = Lot.query
            query = self.visibility_filter(query)
            query = self.type_filter(query, args)
            if args['search']:
                query = query.filter(Lot.name.ilike(args['search'] + '%'))
            lots = query.paginate(per_page=6 if args['search'] else query.count())
            return things_response(
                self.get_lots_dump(lots),
                lots.page,
                lots.per_page,
                lots.total,
                lots.prev_num,
                lots.next_num,
            )
        return jsonify(ret)

    def get_lots_dump(self, lots):
        lots_dump = self.schema.dump(lots.items, many=True, nested=2)
        for lot in lots.items:
            if not lot.transfer:
                continue
            for _lot in lots_dump:
                if _lot['id'] == str(lot.id):
                    _lot['transfer'] = lot.type_transfer()
                    break
        return lots_dump

    def visibility_filter(self, query):
        query = (
            query.outerjoin(Trade)
            .outerjoin(Transfer)
            .filter(
                or_(
                    Trade.user_from == g.user,
                    Trade.user_to == g.user,
                    Lot.owner_id == g.user.id,
                    Transfer.user_from == g.user,
                    Transfer.user_to == g.user,
                )
            )
        )
        return query

    def type_filter(self, query, args):
        lot_type = args.get('type')

        # temporary
        if lot_type == "temporary":
            return query.filter(Lot.trade == None).filter(
                or_(Lot.transfer == None, Transfer.date == None)
            )

        if lot_type == "incoming":
            return query.filter(
                or_(
                    Lot.trade and Trade.user_to == g.user,
                    Lot.transfer and Transfer.user_to == g.user,
                )
            ).all()

        if lot_type == "outgoing":
            return query.filter(
                or_(
                    Lot.trade and Trade.user_from == g.user,
                    Lot.transfer and Transfer.user_from == g.user,
                )
            ).all()

        return query

    def query(self, args):
        query = Lot.query.distinct()
        return query

    def delete(self, id):
        lot = Lot.query.filter_by(id=id, owner=g.user).one()
        lot.delete()
        db.session.commit()
        return Response(status=204)

    @classmethod
    def ui_tree(cls) -> List[Dict]:
        tree = []
        for model in Path.query:  # type: Path
            path = deque(model.path.path.split('.'))
            cls._p(tree, path)
        return tree

    @classmethod
    def _p(cls, nodes: List[Dict[str, Union[uuid.UUID, List]]], path: deque):
        """Recursively creates the nested lot structure.

        Every recursive step consumes path (a deque of lot_id),
        trying to find it as the value of id in nodes, otherwise
        it adds itself. Then moves to the node's children.
        """
        lot_id = uuid.UUID(path.popleft().replace('_', '-'))
        try:
            # does lot_id exist already in node?
            node = next(part for part in nodes if lot_id == part['id'])
        except StopIteration:
            node = {'id': lot_id, 'nodes': []}
            nodes.append(node)
        if path:
            cls._p(node['nodes'], path)

    def get_lot_amount(self, l: Lot):
        """Return lot amount value"""
        return l.amount

    def change_state(self):
        """Change state of Lot"""
        pass

    def transfer_ownership_lot(self):
        """Perform a InitTransfer action to change author_id of lot"""
        pass


class LotBaseChildrenView(View):
    """Base class for adding / removing children devices and
    lots from a lot.
    """

    def __init__(self, definition: 'Resource', **kw) -> None:
        super().__init__(definition, **kw)
        self.list_args = self.ListArgs()

    def get_ids(self) -> Set[uuid.UUID]:
        args = self.QUERY_PARSER.parse(
            self.list_args, request, locations=('querystring',)
        )
        return set(args['id'])

    def get_lot(self, id: uuid.UUID) -> Lot:
        return Lot.query.filter_by(id=id).one()

    # noinspection PyMethodOverriding
    def post(self, id: uuid.UUID):
        lot = self.get_lot(id)
        self._post(lot, self.get_ids())

        db.session().final_flush()
        ret = self.schema.jsonify(lot)
        ret.status_code = 201

        db.session.commit()
        return ret

    def delete(self, id: uuid.UUID):
        lot = self.get_lot(id)
        self._delete(lot, self.get_ids())
        db.session().final_flush()
        response = self.schema.jsonify(lot)
        db.session.commit()
        return response

    def _post(self, lot: Lot, ids: Set[uuid.UUID]):
        raise NotImplementedError

    def _delete(self, lot: Lot, ids: Set[uuid.UUID]):
        raise NotImplementedError


class LotChildrenView(LotBaseChildrenView):
    """View for adding and removing child lots from a lot.

    Ex. ``lot/<id>/children/id=X&id=Y``.
    """

    class ListArgs(ma.Schema):
        id = ma.fields.List(ma.fields.UUID())

    def _post(self, lot: Lot, ids: Set[uuid.UUID]):
        lot.add_children(*ids)

    def _delete(self, lot: Lot, ids: Set[uuid.UUID]):
        lot.remove_children(*ids)


class LotDeviceView(LotBaseChildrenView):
    """View for adding and removing child devices from a lot.

    Ex. ``lot/<id>/devices/id=X&id=Y``.
    """

    class ListArgs(ma.Schema):
        id = ma.fields.List(ma.fields.Integer())

    def _post(self, lot: Lot, ids: Set[int]):
        # get only new devices
        ids -= {x.id for x in lot.devices}
        if not ids:
            return

        devices = set(
            Device.query.filter(Device.id.in_(ids)).filter(Device.owner == g.user)
        )
        devices = set()
        dev_qry = Device.query.filter(Device.id.in_(ids)).filter(Device.owner == g.user)

        for dev in dev_qry:
            if isinstance(dev, DataStorage) and not dev.orphan:
                continue
            devices.add(dev)

        lot.devices.update(devices)

        if lot.trade:
            lot.trade.devices = lot.devices
            if g.user in [lot.trade.user_from, lot.trade.user_to]:
                confirm = Confirm(action=lot.trade, user=g.user, devices=devices)
                db.session.add(confirm)

    def _delete(self, lot: Lot, ids: Set[int]):
        # if there are some devices in ids than not exist now in the lot, then exit
        if not ids.issubset({x.id for x in lot.devices}):
            return

        if lot.trade:
            devices = Device.query.filter(Device.id.in_(ids)).all()
            return delete_from_trade(lot, devices)

        if not g.user == lot.owner:
            txt = 'This is not your lot'
            raise ma.ValidationError(txt)

        devices = set(
            Device.query.filter(Device.id.in_(ids)).filter(Device.owner_id == g.user.id)
        )

        lot.devices.difference_update(devices)


def delete_from_trade(lot: Lot, devices: List):
    users = [lot.trade.user_from, lot.trade.user_to]
    if g.user not in users:
        # theoretically this case is impossible
        txt = 'This is not your trade'
        raise ma.ValidationError(txt)

    # we need lock the action revoke for devices than travel for futures trades
    for dev in devices:
        if dev.owner not in users:
            txt = 'This is not your device'
            raise ma.ValidationError(txt)

    drop_of_lot = []
    without_confirms = []
    for dev in devices:
        if dev.trading(lot) in ['NeedConfirmation', 'Confirm', 'NeedConfirmRevoke']:
            drop_of_lot.append(dev)
            dev.reset_owner()

        if not lot.trade.confirm:
            drop_of_lot.append(dev)
            without_confirms.append(dev)
            dev.reset_owner()

    revoke = Revoke(action=lot.trade, user=g.user, devices=set(devices))
    db.session.add(revoke)

    if without_confirms:
        phantom = lot.trade.user_to
        if lot.trade.user_to == g.user:
            phantom = lot.trade.user_from

        phantom_revoke = Revoke(
            action=lot.trade, user=phantom, devices=set(without_confirms)
        )
        db.session.add(phantom_revoke)

    lot.devices.difference_update(OrderedSet(drop_of_lot))
    return revoke
