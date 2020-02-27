from marshmallow import fields as f
from teal.marshmallow import SanitizedStr, URL, EnumField

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.deliverynote import models as m
from ereuse_devicehub.resources.user import schemas as s_user
from ereuse_devicehub.resources.models import STR_SIZE
from ereuse_devicehub.resources.schemas import Thing


class Deliverynote(Thing):
    id = f.UUID(dump_only=True)
    documentID = SanitizedStr(validate=f.validate.Length(max=STR_SIZE), required=True)
    url = URL(dump_only=True, description=m.Deliverynote.url.__doc__)
    creator = NestedOn(s_user.User,only_query='id')
    supplier = NestedOn(s_user.User,only_query='id')
    # deposit = f.Integer(validate=f.validate.Range(min=0, max=100),
    #                    description=m.Lot.deposit.__doc__)
    deposit = SanitizedStr(validate=f.validate.Length(max=STR_SIZE), required=True)
    expected_devices = SanitizedStr(validate=f.validate.Length(max=STR_SIZE), required=True)
    transferred_devices = SanitizedStr(validate=f.validate.Length(max=STR_SIZE), required=True)
    transfer_state = EnumField(TransferState, description=m.Lot.transfer_state.comment)
