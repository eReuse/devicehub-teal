from marshmallow import fields as f

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.deliverynote import models as m
from ereuse_devicehub.resources.enums import TransferState
from ereuse_devicehub.resources.models import STR_SIZE
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.user import schemas as s_user
from ereuse_devicehub.teal.marshmallow import EnumField, SanitizedStr


class Deliverynote(Thing):
    id = f.UUID(dump_only=True)
    document_id = SanitizedStr(
        validate=f.validate.Length(max=STR_SIZE), required=True, data_key='documentID'
    )
    creator = NestedOn(s_user.User, dump_only=True)
    supplier_email = SanitizedStr(
        validate=f.validate.Length(max=STR_SIZE),
        load_only=True,
        required=True,
        data_key='supplierEmail',
    )
    supplier = NestedOn(s_user.User, dump_only=True)
    receiver = NestedOn(s_user.User, dump_only=True)
    date = f.DateTime('iso', required=True)
    amount = f.Integer(
        validate=f.validate.Range(min=0, max=100),
        description=m.Deliverynote.amount.__doc__,
    )
    expected_devices = f.List(f.Dict, required=True, data_key='expectedDevices')
    transferred_devices = f.List(
        f.Integer(), required=False, data_key='transferredDevices'
    )
    transfer_state = EnumField(TransferState, description=m.Lot.transfer_state.comment)
