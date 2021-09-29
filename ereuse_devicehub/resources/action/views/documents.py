import copy

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import DataWipe
from ereuse_devicehub.resources.documents.models import DataWipeDocument
from ereuse_devicehub.resources.device.models import DataStorage
from ereuse_devicehub.resources.documents.schemas import DataWipeDocument as sh_document
from ereuse_devicehub.resources.hash_reports import ReportHash


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
        self.document = DataWipeDocument(**doc_data)
        db.session.add(self.document)

        db_hash = ReportHash(hash3=self.document.file_hash)
        db.session.add(db_hash)

    def insert_action(self, data):
        [data.pop(x, None) for x in ['url', 'documentId', 'filename', 'hash', 'software', 'success']]
        self.data = self.schema.load(data)

        for dev in self.data['devices']:
            if not hasattr(dev, 'components'):
                continue

            for component in dev.components:
                if isinstance(component, DataStorage):
                    self.data['devices'].add(component)

        self.data['document'] = self.document
        self.erased = DataWipe(**self.data)
        db.session.add(self.erased)
