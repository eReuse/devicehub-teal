from marshmallow.fields import DateTime, Integer, validate
from teal.marshmallow import SanitizedStr, URL
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.documents import models as m
# from marshmallow import ValidationError, validates_schema


class EraseDocument(Thing):
    __doc__ = m.EraseDocument.__doc__
    id = Integer(description=m.EraseDocument.id.comment, dump_only=True)
    type = SanitizedStr(default='EraseDocument')
    date = DateTime(data_key='endTime', 
                    required=False, 
                    description=m.EraseDocument.date.comment)
    id_document = SanitizedStr(data_key='documentId', 
                               default='', 
                               description=m.EraseDocument.id_document.comment)
    file_name = SanitizedStr(data_key='filename',
                             default='',
                             description=m.EraseDocument.file_name.comment, 
                             validate=validate.Length(max=100))
    file_hash = SanitizedStr(data_key='hash',
                             default='',
                             description=m.EraseDocument.file_hash.comment,
                             validate=validate.Length(max=64))
    url = URL(description=m.EraseDocument.url.comment)
