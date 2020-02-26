from marshmallow import fields as f
from teal.marshmallow import SanitizedStr, URL, EnumField

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.deliverynote import models as m
from ereuse_devicehub.resources.models import STR_SIZE
from ereuse_devicehub.resources.schemas import Thing


class DeliveryNote(Thing):
    id = f.UUID(dump_only=True)
    documentID = SanitizedStr(validate=f.validate.Length(max=STR_SIZE), required=True)
    url = URL(dump_only=True, description=m.DeliveryNote.url.__doc__)
