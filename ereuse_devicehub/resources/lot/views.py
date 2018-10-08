import uuid
from collections import deque
from enum import Enum
from typing import List, Set

import marshmallow as ma
from flask import jsonify, request
from marshmallow import Schema as MarshmallowSchema, fields as f
from teal.marshmallow import EnumField
from teal.resource import View

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.lot.models import Lot, Path


class LotFormat(Enum):
    UiTree = 'UiTree'


class LotView(View):
    class FindArgs(MarshmallowSchema):
        """
        Allowed arguments for the ``find``
        method (GET collection) endpoint
        """
        format = EnumField(LotFormat, missing=None)
        search = f.Str(missing=None)

    def post(self):
        l = request.get_json()
        lot = Lot(**l)
        db.session.add(lot)
        db.session.commit()
        ret = self.schema.jsonify(lot)
        ret.status_code = 201
        return ret

    def one(self, id: uuid.UUID):
        """Gets one event."""
        lot = Lot.query.filter_by(id=id).one()  # type: Lot
        return self.schema.jsonify(lot)

    def find(self, args: dict):
        """
        Gets lots.

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
            nodes = []
            for model in Path.query:  # type: Path
                path = deque(model.path.path.split('.'))
                self._p(nodes, path)
            return jsonify({
                'items': nodes,
                'url': request.path
            })
        else:
            query = Lot.query
            if args['search']:
                query = query.filter(Lot.name.ilike(args['search'] + '%'))
            lots = query.paginate(per_page=6 if args['search'] else 30)
            ret = {
                'items': self.schema.dump(lots.items, many=True, nested=0),
                'pagination': {
                    'page': lots.page,
                    'perPage': lots.per_page,
                    'total': lots.total,
                    'previous': lots.prev_num,
                    'next': lots.next_num
                },
                'url': request.path
            }
            return jsonify(ret)

    def _p(self, nodes: List[dict], path: deque):
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
            lot = Lot.query.filter_by(id=lot_id).one()
            node = {
                'id': lot_id,
                'name': lot.name,
                'url': lot.url.to_text(),
                'closed': lot.closed,
                'updated': lot.updated,
                'created': lot.created,
                'nodes': []
            }
            nodes.append(node)
        if path:
            self._p(node['nodes'], path)


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
        db.session.commit()

        ret = self.schema.jsonify(lot)
        ret.status_code = 201
        return ret

    def delete(self, id: uuid.UUID):
        lot = self.get_lot(id)
        self._delete(lot, self.get_ids())
        db.session.commit()
        return self.schema.jsonify(lot)

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
        for id in ids:
            lot.add_child(id)  # todo what to do if child exists already?

    def _delete(self, lot: Lot, ids: Set[uuid.UUID]):
        for id in ids:
            lot.remove_child(id)


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
