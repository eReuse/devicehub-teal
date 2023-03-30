from marshmallow.fields import Boolean
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.agent.schemas import Organization
from ereuse_devicehub.resources.device.schemas import Device
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.tag import model as m
from ereuse_devicehub.resources.user.schemas import User
from ereuse_devicehub.teal.marshmallow import URL, SanitizedStr


def without_slash(x: str) -> bool:
    """Returns true if x does not contain a slash."""
    return '/' not in x


class Tag(Thing):
    id = SanitizedStr(
        lower=True, description=m.Tag.id.comment, validator=without_slash, required=True
    )
    provider = URL(description=m.Tag.provider.comment, validator=without_slash)
    device = NestedOn(Device, dump_only=True)
    owner = NestedOn(User, only_query='id')
    org = NestedOn(Organization, collection_class=OrderedSet, only_query='id')
    secondary = SanitizedStr(lower=True, description=m.Tag.secondary.comment)
    printable = Boolean(dump_only=True, decsription=m.Tag.printable.__doc__)
    url = URL(dump_only=True, description=m.Tag.url.__doc__)
    code = SanitizedStr(dump_only=True, description=m.Tag.internal_id.comment)
