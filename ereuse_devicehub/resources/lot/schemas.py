from marshmallow import fields as f
from teal.marshmallow import SanitizedStr

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.device.schemas import Device
from ereuse_devicehub.resources.lot import models as m
from ereuse_devicehub.resources.models import STR_SIZE
from ereuse_devicehub.resources.schemas import Thing


class Lot(Thing):
    id = f.UUID(dump_only=True)
    name = SanitizedStr(validate=f.validate.Length(max=STR_SIZE), required=True)
    closed = f.Boolean(missing=False, description=m.Lot.closed.comment)
    devices = NestedOn(Device, many=True, dump_only=True)
    children = NestedOn('Lot', many=True, dump_only=True)
    parents = NestedOn('Lot', many=True, dump_only=True)
