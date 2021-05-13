from marshmallow.fields import DateTime, Integer
from teal.marshmallow import SanitizedStr

from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.tradedocument import models as m


class Document(Thing):
    __doc__ = m.Document.__doc__
    id = Integer(description=m.Document.id.comment, dump_only=True)
    date = DateTime(required=False, description=m.Document.date.comment)
    id_document = SanitizedStr(default='', description=m.Document.id_document.comment)
    description = SanitizedStr(default='', description=m.Document.description.comment)
    file_name = SanitizedStr(default='', description=m.Document.file_name.comment)
