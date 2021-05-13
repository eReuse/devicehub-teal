
import marshmallow
from flask import g, current_app as app, render_template, request, Response
from flask.json import jsonify
from flask_sqlalchemy import Pagination
from marshmallow import fields, fields as f, validate as v, Schema as MarshmallowSchema
from teal.resource import View

from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.query import SearchQueryParser, things_response
from ereuse_devicehub.resources.tradedocument.models import Document

class DocumentView(View):

    # @auth.Auth.requires_auth
    def one(self, id: str):
        document = Document.query.filter_by(id=id).first()
        return self.schema.jsonify(document)

    # @auth.Auth.requires_auth
    def post(self):
        """Posts an action."""
        json = request.get_json(validate=False)
        resource_def = app.resources[json['type']]

        a = resource_def.schema.load(json)
        Model = db.Model._decl_class_registry.data[json['type']]()
        action = Model(**a)
        db.session.add(action)
        db.session().final_flush()
        ret = self.schema.jsonify(action)
        ret.status_code = 201
        db.session.commit()
        return ret
