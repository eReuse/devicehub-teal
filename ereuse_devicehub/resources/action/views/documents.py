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
from ereuse_devicehub.resources.documents.models import EraseDocument
from ereuse_devicehub.resources.documents.schemas import EraseDocument as sh_document


class ErasedView():
    """Handler for manager the trade action register from post

       request_post = {
           'type': 'Trade',
           'devices': [device_id],
           'documents': [document_id],
           'userFrom': user2.email,
           'userTo': user.email,
           'price': 10,
           'date': "2020-12-01T02:00:00+00:00",
           'lot': lot['id'],
           'confirm': True,
       }

    """

    def __init__(self, data, schema):
        self.schema = schema
        self.insert_document(copy.copy(data))
        self.insert_action(copy.copy(data))

    def post(self):
        # import pdb; pdb.set_trace()
        db.session().final_flush()
        ret = self.schema.jsonify(self.erased)
        ret.status_code = 201
        db.session.commit()
        return ret

    def insert_document(self, data):
        # import pdb; pdb.set_trace()
        schema = sh_document()
        [data.pop(x) for x in ['severity', 'devices', 'name', 'description']]
        doc_data = schema.load(data)
        doc_data['type'] = 'ToErased'
        self.document = EraseDocument(**doc_data)
        db.session.add(self.document)
        # db.session.commit()

    def insert_action(self, data):
        import pdb; pdb.set_trace()
        [data.pop(x, None) for x in ['url', 'documentId', 'filename', 'hash']]
        # self.data = self.schema.load(data)
        # self.data['document_id'] = self.document.id
        # self.data['document'] = self.document
        # data['document_id'] = self.document.id
        data['document'] = self.document
        self.erased = ToErased(**data)
        db.session.add(self.erased)
