from marshmallow.fields import DateTime, Integer
from teal.marshmallow import SanitizedStr

from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.tradedocument import models as m


class TradeDocument(Thing):
    __doc__ = m.TradeDocument.__doc__
    id = Integer(description=m.TradeDocument.id.comment, dump_only=True)
    date = DateTime(required=False, description=m.TradeDocument.date.comment)
    id_document = SanitizedStr(default='', description=m.TradeDocument.id_document.comment)
    description = SanitizedStr(default='', description=m.TradeDocument.description.comment)
    file_name = SanitizedStr(default='', description=m.TradeDocument.file_name.comment)
    # lot = NestedOn('Lot', dump_only=True, description=m.TradeDocument.lot.__doc__)
