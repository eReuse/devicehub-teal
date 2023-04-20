from marshmallow.fields import DateTime, Float, Integer, validate

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.tradedocument import models as m
from ereuse_devicehub.teal.marshmallow import URL, SanitizedStr

# from marshmallow import ValidationError, validates_schema


# from ereuse_devicehub.resources.lot import schemas as s_lot


class TradeDocument(Thing):
    __doc__ = m.TradeDocument.__doc__
    id = Integer(description=m.TradeDocument.id.comment, dump_only=True)
    date = DateTime(required=False, description=m.TradeDocument.date.comment)
    id_document = SanitizedStr(
        data_key='documentId',
        default='',
        description=m.TradeDocument.id_document.comment,
    )
    description = SanitizedStr(
        default='',
        description=m.TradeDocument.description.comment,
        validate=validate.Length(max=500),
    )
    file_name = SanitizedStr(
        data_key='filename',
        default='',
        description=m.TradeDocument.file_name.comment,
        validate=validate.Length(max=100),
    )
    file_hash = SanitizedStr(
        data_key='hash',
        default='',
        description=m.TradeDocument.file_hash.comment,
        validate=validate.Length(max=64),
    )
    url = URL(description=m.TradeDocument.url.comment)
    lot = NestedOn('Lot', only_query='id', description=m.TradeDocument.lot.__doc__)
    trading = SanitizedStr(dump_only=True, description='')
    weight = Float(required=False, description=m.TradeDocument.weight.comment)
    total_weight = Float(required=False, description=m.TradeDocument.weight.comment)
