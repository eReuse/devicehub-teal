from marshmallow import fields as f

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.device.schemas import Device
from ereuse_devicehub.resources.lot import models as m
from ereuse_devicehub.resources.models import STR_SIZE
from ereuse_devicehub.resources.schemas import Thing


class Lot(Thing):
    id = f.UUID(dump_only=True)
    name = f.String(validate=f.validate.Length(max=STR_SIZE))
    closed = f.String(required=True, missing=False, description=m.Lot.closed.comment)
    devices = f.String(NestedOn(Device, many=True, collection_class=set, only_query='id'))
