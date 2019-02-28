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
    org_id = ...  # type: Column
    org = ...  # type: relationship
    provider = ...  # type: Column
    device_id = ...  # type: Column
    device = ...  # type: relationship
    secondary = ...  # type: Column

    def __init__(self, id: str,
                 org: Organization = None,
                 secondary: str = None,
                 provider: URL = None,
                 device: Device = None) -> None:
        super().__init__()
        self.id = ...  # type: str
        self.org_id = ...  # type: UUID
        self.org = ...  # type: Organization
        self.provider = ...  # type: URL
        self.device_id = ...  # type: int
        self.device = ...  # type: Device
        self.secondary = ...  # type: str

    @classmethod
    def from_an_id(cls, id: str) -> Query:
        pass

    def like_etag(self) -> bool:
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
