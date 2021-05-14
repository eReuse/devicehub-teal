
import marshmallow
from flask import g, current_app as app, render_template, request, Response
from flask.json import jsonify
from flask_sqlalchemy import Pagination
from marshmallow import fields, fields as f, validate as v, Schema as MarshmallowSchema
from teal.resource import View

from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.query import SearchQueryParser, things_response
from ereuse_devicehub.resources.tradedocument.models import TradeDocument

class TradeDocumentView(View):

    def one(self, id: str):
        doc = TradeDocument.query.filter_by(id=id, owner=g.user).one()
        return self.schema.jsonify(doc)

    def post(self):
        """Add one document."""
        data = request.get_json(validate=True)
        doc = TradeDocument(**data)
        db.session.add(doc)
        db.session().final_flush()
        ret = self.schema.jsonify(doc)
        ret.status_code = 201
        db.session.commit()
        return ret

    def delete(self, id):
        doc = TradeDocument.query.filter_by(id=id, owner=g.user).one()
        db.session.delete(doc)
        db.session.commit()
        return Response(status=204)
