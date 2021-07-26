import copy

from flask import g
from sqlalchemy.util import OrderedSet
from teal.marshmallow import ValidationError

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import (Trade, Confirm, ConfirmRevoke, 
                                                      Revoke, RevokeDocument, ConfirmDocument,
                                                      ConfirmRevokeDocument)
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.action.models import ToErased
from ereuse_devicehub.resources.documents.models import Document
from ereuse_devicehub.resources.device.models import DataStorage 
from ereuse_devicehub.resources.documents.schemas import Document as sh_document


class ErasedView():
    """Handler for manager the action register for add to a device one proof of erase
    """

    def __init__(self, data, schema):
        self.schema = schema
        self.insert_document(copy.copy(data))
        self.insert_action(copy.copy(data))

    def post(self):
        db.session().final_flush()
        from flask import jsonify
        ret = jsonify(self.erased)
        ret.status_code = 201
        db.session.commit()
        return ret

    def insert_document(self, data):
        schema = sh_document()
        [data.pop(x, None) for x in ['severity', 'devices', 'name', 'description']]
        doc_data = schema.load(data)
        doc_data['type'] = 'ToErased'
        self.document = Document(**doc_data)
        db.session.add(self.document)

    def insert_action(self, data):
        [data.pop(x, None) for x in ['url', 'documentId', 'filename', 'hash']]
        self.data = self.schema.load(data)
       
        for dev in self.data['devices']:
            if not hasattr(dev, 'components'):
                continue

            for component in dev.components:
                if isinstance(component, DataStorage):
                    self.data['devices'].add(component)

        self.data['document'] = self.document
        self.erased = ToErased(**self.data)
        db.session.add(self.erased)
