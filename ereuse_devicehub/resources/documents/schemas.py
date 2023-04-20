from marshmallow import post_load
from marshmallow.fields import Boolean, DateTime, Float, Integer, validate
from marshmallow.validate import Range

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.documents import models as m
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.tradedocument.models import TradeDocument
from ereuse_devicehub.teal.marshmallow import URL, SanitizedStr


class DataWipeDocument(Thing):
    __doc__ = m.DataWipeDocument.__doc__
    id = Integer(description=m.DataWipeDocument.id.comment, dump_only=True)
    url = URL(required=False, description=m.DataWipeDocument.url.comment)
    success = Boolean(
        required=False, default=False, description=m.DataWipeDocument.success.comment
    )
    software = SanitizedStr(description=m.DataWipeDocument.software.comment)
    date = DateTime(
        data_key='endTime', required=False, description=m.DataWipeDocument.date.comment
    )
    id_document = SanitizedStr(
        data_key='documentId',
        required=False,
        default='',
        description=m.DataWipeDocument.id_document.comment,
    )
    file_name = SanitizedStr(
        data_key='filename',
        default='',
        description=m.DataWipeDocument.file_name.comment,
        validate=validate.Length(max=100),
    )
    file_hash = SanitizedStr(
        data_key='hash',
        default='',
        description=m.DataWipeDocument.file_hash.comment,
        validate=validate.Length(max=64),
    )

    @post_load
    def get_trade_document(self, data):
        data['document_type'] = 'DataWipeDocument'
