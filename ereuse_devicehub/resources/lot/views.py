import datetime
import uuid
from collections import deque
from enum import Enum
from typing import Dict, List, Set, Union

import marshmallow as ma
import teal.cache
from flask import Response, jsonify, request
from marshmallow import Schema as MarshmallowSchema, fields as f
from teal.marshmallow import EnumField
from teal.resource import View
from sqlalchemy.orm import joinedload

from ereuse_devicehub.db import db
from ereuse_devicehub.query import things_response
from ereuse_devicehub.resources.device.models import Device, Computer
from ereuse_devicehub.resources.lot.models import Lot, Path


class LotFormat(Enum):
    UiTree = 'UiTree'


class LotView(View):
    class FindArgs(MarshmallowSchema):
        """Allowed arguments for the ``find``
        method (GET collection) endpoint
        """
        format = EnumField(LotFormat, missing=None)
        search = f.Str(missing=None)

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
        patch_schema = self.resource_def.SCHEMA(only=('name', 'description', 'transfer_state', 'receiver_id', 'deposit', 'delivery_note_address', 'devices'), partial=True)
        l = request.get_json(schema=patch_schema)
        lot = Lot.query.filter_by(id=id).one()
        device_fields = ['transfer_state', 'receiver_id', 'deposit', 'delivery_note_address']
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
        return self.schema.jsonify(lot)

    @teal.cache.cache(datetime.timedelta(minutes=5))
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
            lots = self.schema.dump(Lot.query, many=True, nested=1)
            ret = {
                'items': {l['id']: l for l in lots},
                'tree': self.ui_tree(),
                'url': request.path
            }
        else:
            query = Lot.query
            if args['search']:
                query = query.filter(Lot.name.ilike(args['search'] + '%'))
            lots = query.paginate(per_page=6 if args['search'] else 30)
            return things_response(
                self.schema.dump(lots.items, many=True, nested=0),
                lots.page, lots.per_page, lots.total, lots.prev_num, lots.next_num
            )
        return jsonify(ret)

    def delete(self, id):
        lot = Lot.query.filter_by(id=id).one()
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
            node = {
                'id': lot_id,
                'nodes': []
            }
            nodes.append(node)
        if path:
            cls._p(node['nodes'], path)


class LotBaseChildrenView(View):
    """Base class for adding / removing children devices and
     lots from a lot.
     """

    def __init__(self, definition: 'Resource', **kw) -> None:
        super().__init__(definition, **kw)
        self.list_args = self.ListArgs()

    def get_ids(self) -> Set[uuid.UUID]:
        args = self.QUERY_PARSER.parse(self.list_args, request, locations=('querystring',))
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
        lot.devices.update(Device.query.filter(Device.id.in_(ids)))

    def _delete(self, lot: Lot, ids: Set[int]):
        lot.devices.difference_update(Device.query.filter(Device.id.in_(ids)))
