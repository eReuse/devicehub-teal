from marshmallow.fields import DateTime, Integer
from teal.marshmallow import SanitizedStr, URL
# from marshmallow import ValidationError, validates_schema

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.tradedocument import models as m
# from ereuse_devicehub.resources.lot import schemas as s_lot


class TradeDocument(Thing):
    __doc__ = m.TradeDocument.__doc__
    id = Integer(description=m.TradeDocument.id.comment, dump_only=True)
    date = DateTime(required=False, description=m.TradeDocument.date.comment)
    id_document = SanitizedStr(data_key='documentId', 
                               default='', 
                               description=m.TradeDocument.id_document.comment)
    description = SanitizedStr(default='', 
                               description=m.TradeDocument.description.comment)
    file_name = SanitizedStr(data_key='filename',
                             default='',
                             description=m.TradeDocument.file_name.comment)
    file_hash = SanitizedStr(data_key='hash',
                             default='',
                             description=m.TradeDocument.file_hash.comment)
    url = URL(description=m.TradeDocument.url.comment)
    lot = NestedOn('Lot', only_query='id', description=m.TradeDocument.lot.__doc__)
    # lot = NestedOn(s_lot.Lot, only_query='id', description=m.TradeDocument.lot.__doc__)
