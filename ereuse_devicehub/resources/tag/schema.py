from marshmallow import fields as f
from sqlalchemy.util import OrderedSet
from teal.marshmallow import SanitizedStr, URL

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.agent.schemas import Organization
from ereuse_devicehub.resources.device.schemas import Device
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.tag import model as m


def without_slash(x: str) -> bool:
    """Returns true if x does not contain a slash."""
    return '/' not in x


class Tag(Thing):
    id = f.UUID(dump_only=True)
    name_tag = SanitizedStr(lower=True, description=m.Tag.name_tag.comment)
    device = NestedOn(Device, dump_only=True)
    org = NestedOn(Organization, collection_class=OrderedSet, only_query='id')
    printable = f.Boolean(dump_only=True, decsription=m.Tag.printable.__doc__)
    url = URL(dump_only=True, description=m.Tag.url.__doc__)
