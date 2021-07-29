from marshmallow.fields import DateTime, Integer, validate, Boolean
from teal.marshmallow import SanitizedStr, URL
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.documents import models as m
# from marshmallow import ValidationError, validates_schema


class Document(Thing):
    __doc__ = m.Document.__doc__
    id = Integer(description=m.Document.id.comment, dump_only=True)
    type = SanitizedStr(default='Document')
    url = URL(description=m.Document.url.comment)
    success = Boolean(description=m.Document.success.comment)
    software = SanitizedStr(description=m.Document.software.comment)
    date = DateTime(data_key='endTime', 
                    required=False, 
                    description=m.Document.date.comment)
    id_document = SanitizedStr(data_key='documentId', 
                               default='', 
                               description=m.Document.id_document.comment)
    file_name = SanitizedStr(data_key='filename',
                             default='',
                             description=m.Document.file_name.comment, 
                             validate=validate.Length(max=100))
    file_hash = SanitizedStr(data_key='hash',
                             default='',
                             description=m.Document.file_hash.comment,
                             validate=validate.Length(max=64))
