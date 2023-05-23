from marshmallow import fields as f

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.action import schemas as s_action
from ereuse_devicehub.resources.deliverynote import schemas as s_deliverynote
from ereuse_devicehub.resources.device import schemas as s_device
from ereuse_devicehub.resources.enums import TransferState
from ereuse_devicehub.resources.lot import models as m
from ereuse_devicehub.resources.models import STR_SIZE
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.teal.marshmallow import URL, EnumField, SanitizedStr

TRADE_VALUES = (
    'id',
    'user_from.email',
    'user_to.email',
    'user_from.id',
    'user_to.id',
    'user_to.code',
    'user_from.code',
)


DOCUMENTS_VALUES = ('id', 'file_name', 'total_weight', 'trading')


class Old_Lot(Thing):
    id = f.UUID(dump_only=True)
    name = SanitizedStr(validate=f.validate.Length(max=STR_SIZE), required=True)
    description = SanitizedStr(description=m.Lot.description.comment)
    closed = f.Boolean(missing=False, description=m.Lot.closed.comment)
    devices = NestedOn(s_device.Device, many=True, dump_only=True)
    children = NestedOn('Lot', many=True, dump_only=True)
    parents = NestedOn('Lot', many=True, dump_only=True)
    url = URL(dump_only=True, description=m.Lot.url.__doc__)
    amount = f.Integer(
        validate=f.validate.Range(min=0, max=100), description=m.Lot.amount.__doc__
    )
    # author_id = NestedOn(s_user.User,only_query='author_id')
    owner_id = f.UUID(data_key='ownerID')
    transfer_state = EnumField(TransferState, description=m.Lot.transfer_state.comment)
    receiver_address = SanitizedStr(validate=f.validate.Length(max=42))
    deliverynote = NestedOn(s_deliverynote.Deliverynote, dump_only=True)
    documents = NestedOn('TradeDocument', many=True, dump_only=True)


class Lot(Thing):
    id = f.UUID(dump_only=True)
    name = SanitizedStr(validate=f.validate.Length(max=STR_SIZE), required=True)
    description = SanitizedStr(description=m.Lot.description.comment)
    trade = f.Nested(s_action.Trade, dump_only=True, only=TRADE_VALUES)
    documents = f.Nested(
        'TradeDocument', many=True, dump_only=True, only=DOCUMENTS_VALUES
    )
