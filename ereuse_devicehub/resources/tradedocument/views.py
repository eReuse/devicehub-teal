import os
import time
from datetime import datetime

from flask import Response
from flask import current_app as app
from flask import g, request
from marshmallow import ValidationError

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import ConfirmDocument
from ereuse_devicehub.resources.hash_reports import ReportHash
from ereuse_devicehub.resources.tradedocument.models import TradeDocument
from ereuse_devicehub.teal.resource import View


class TradeDocumentView(View):
    def one(self, id: str):
        doc = TradeDocument.query.filter_by(id=id, owner=g.user).one()
        return self.schema.jsonify(doc)

    def post(self):
        """Add one document."""

        try:
            data = request.get_json(validate=True)
        except ValueError as err:
            raise ValidationError(err)

        hash3 = data['file_hash']
        db_hash = ReportHash(hash3=hash3)
        db.session.add(db_hash)

        doc = TradeDocument(**data)
        trade = doc.lot.trade
        if trade:
            trade.documents.add(doc)
            confirm = ConfirmDocument(
                action=trade, user=g.user, devices=set(), documents={doc}
            )
            db.session.add(confirm)
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
