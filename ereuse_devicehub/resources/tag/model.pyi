from uuid import UUID

from boltons import urlutils
from boltons.urlutils import URL
from sqlalchemy import Column
from sqlalchemy.orm import relationship
from teal.db import Query

from ereuse_devicehub.resources.agent.models import Organization
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.models import Thing


class Tag(Thing):
    id = ...  # type: Column
    name_tag = ... # type: Column
    org_id = ...  # type: Column
    org = ...  # type: relationship
    device_id = ...  # type: Column
    device = ...  # type: relationship

    def __init__(self, id: str,
                 org: Organization = None,
                 secondary: str = None,
                 device: Device = None) -> None:
        super().__init__()
        self.id = ...  # type: UUID
        self.name_tag = ...  # type: str
        self.org_id = ...  # type: UUID
        self.org = ...  # type: Organization
        self.device_id = ...  # type: int
        self.device = ...  # type: Device

    @classmethod
    def from_an_id(cls, name_tag: str) -> Query:
        pass

    @property
    def printable(self) -> bool:
        pass

    @classmethod
    def is_printable_q(cls):
        pass

    @property
    def url(self) -> urlutils.URL:
        pass
