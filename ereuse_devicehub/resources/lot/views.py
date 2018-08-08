import uuid

from flask import current_app as app, request

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.lot.models import Lot
from teal.resource import View


class LotView(View):
    def post(self):
        json = request.get_json(validate=False)
        e = app.resources[json['type']].schema.load(json)
        Model = db.Model._decl_class_registry.data[json['type']]()
        lot = Model(**e)
        db.session.add(lot)
        db.session.commit()
        ret = self.schema.jsonify(lot)
        ret.status_code = 201
        return ret

    def one(self, id: uuid.UUID):
        """Gets one event."""
        event = Lot.query.filter_by(id=id).one()
        return self.schema.jsonify(event)
