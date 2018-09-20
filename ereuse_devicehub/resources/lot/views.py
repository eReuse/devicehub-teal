import uuid
from typing import Set

import marshmallow as ma
from flask import request
from teal.resource import View

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.lot.models import Lot


class LotView(View):
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
