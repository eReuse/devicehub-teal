from uuid import UUID

from boltons.urlutils import URL
from sqlalchemy import Column
from sqlalchemy.orm import relationship

from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.models import Thing


class Tag(Thing):
    id = ...  # type: Column
    org_id = ...  # type: Column
    org = ...  # type: relationship
    provider = ...  # type: Column
    device_id = ...  # type: Column
    device = ...  # type: relationship

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = ...  # type: str
        self.org_id = ...  # type: UUID
        self.provider = ...  # type: URL
        self.device_id = ...  # type: int
        self.device = ...  # type: Device
