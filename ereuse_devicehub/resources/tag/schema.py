from marshmallow.fields import String

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.device.schemas import Device
from ereuse_devicehub.resources.schemas import Thing
from teal.marshmallow import URL


class Tag(Thing):
    id = String(description='The ID of the tag.',
                validator=lambda x: '/' not in x,
                required=True)
    provider = URL(description='The provider URL.')
    device = NestedOn(Device, description='The device linked to this tag.')
    org = String(description='The organization that issued the tag.')
