from datetime import datetime, timedelta
from distutils.version import StrictVersion
from typing import List, Set
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.orm import relationship

from ereuse_devicehub.resources.device.models import Component, Computer, Device
from ereuse_devicehub.resources.enums import AppearanceRange, Bios, FunctionalityRange, \
    RatingSoftware, SnapshotSoftware, TestHardDriveLength, SnapshotExpectedEvents
from ereuse_devicehub.resources.image.models import Image
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user import User
from teal.db import Model


class Event(Thing):
    id = ...  # type: Column
    title = ...  # type: Column
    date = ...  # type: Column
    type = ...  # type: Column
    incidence = ...  # type: Column
    description = ...  # type: Column
    finalized = ...  # type: Column
    snapshot_id = ...  # type: Column
    snapshot = ...  # type: relationship
    author_id = ...  # type: Column
    author = ...  # type: relationship
    components = ...  # type: relationship

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = ...  # type: UUID
        self.title = ...  # type: str
        self.type = ...  # type: str
        self.incidence = ...  # type: bool
        self.closed = ...  # type: bool
        self.error = ...  # type: bool
        self.description = ...  # type: str
        self.date = ...  # type: datetime
        self.snapshot_id = ...  # type: UUID
        self.snapshot = ...  # type: Snapshot
        self.author_id = ...  # type: UUID
        self.author = ...  # type: User
        self.components = ...  # type: Set[Component]


class EventWithOneDevice(Event):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.device_id = ...  # type: int
        self.device = ...  # type: Device


class EventWithMultipleDevices(Event):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.devices = ...  # type: Set[Device]


class Step(Model):
    def __init__(self, **kwargs) -> None:
        self.erasure_id = ...  # type: UUID
        self.type = ...  # type: str
        self.num = ...  # type: int
        self.success = ...  # type: bool
        self.start_time = ...  # type: datetime
        self.end_time = ...  # type: datetime
        self.secure_random_steps = ...  # type: int
        self.clean_with_zeros = ...  # type: bool
        self.erasure = ...  # type: EraseBasic


class StepZero(Step):
    pass


class StepRandom(Step):
    pass


class Snapshot(EventWithOneDevice):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.uuid = ...  # type: UUID
        self.version = ...  # type: StrictVersion
        self.software = ...  # type: SnapshotSoftware
        self.elapsed = ...  # type: timedelta
        self.device = ...  # type: Computer
        self.events = ...  # type: Set[Event]
        self.expected_events = ... # type: List[SnapshotExpectedEvents]


class Install(EventWithOneDevice):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = ...  # type: str
        self.elapsed = ...  # type: timedelta
        self.success = ...  # type: bool


class SnapshotRequest(Model):
    def __init__(self, **kwargs) -> None:
        self.id = ...  # type: UUID
        self.request = ...  # type: dict
        self.snapshot = ...  # type: Snapshot


class Rate(EventWithOneDevice):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.rating = ...  # type: float
        self.algorithm_software = ...  # type: RatingSoftware
        self.algorithm_version = ...  # type: StrictVersion
        self.appearance = ...  # type: float
        self.functionality = ...  # type: float
        self.rating_range = ...  # type: str


class IndividualRate(Rate):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.aggregated_ratings = ...  # type: Set[AggregateRate]


class AggregateRate(Rate):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.ratings = ...  # type: Set[IndividualRate]


class WorkbenchRate(IndividualRate):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.processor = ...  # type: float
        self.ram = ...  # type: float
        self.data_storage = ...  # type: float
        self.graphic_card = ...  # type: float
        self.labelling = ...  # type: bool
        self.bios = ...  # type: Bios
        self.appearance_range = ...  # type: AppearanceRange
        self.functionality_range = ...  # type: FunctionalityRange


class PhotoboxRate(IndividualRate):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.num = ...  # type: int
        self.image_id = ...  # type: UUID
        self.image = ...  # type: Image


class PhotoboxUserRate(PhotoboxRate):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.assembling = ...  # type: int
        self.parts = ...  # type: int
        self.buttons = ...  # type: int
        self.dents = ...  # type: int
        self.decolorization = ...  # type: int
        self.scratches = ...  # type: int
        self.tag_adhesive = ...  # type: int
        self.dirt = ...  # type: int


class PhotoboxSystemRate(PhotoboxRate):
    pass


class Test(EventWithOneDevice):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.elapsed = ...  # type: timedelta
        self.success = ...  # type: bool


class TestDataStorage(Test):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = ...  # type: UUID
        self.length = ...  # type: TestHardDriveLength
        self.status = ...  # type: str
        self.lifetime = ...  # type: timedelta
        self.first_error = ...  # type: int
        self.passed_lifetime = ...  # type: timedelta
        self.assessment = ...  # type: int
        self.reallocated_sector_count = ...  # type: int
        self.power_cycle_count = ...  # type: int
        self.reported_uncorrectable_errors = ...  # type: int
        self.command_timeout = ...  # type: int
        self.current_pending_sector_count = ...  # type: int
        self.offline_uncorrectable = ...  # type: int
        self.remaining_lifetime_percentage = ...  # type: int


class StressTest(Test):
    pass


class EraseBasic(EventWithOneDevice):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.start_time = ...  # type: datetime
        self.end_time = ...  # type: datetime
        self.secure_random_steps = ...  # type: int
        self.steps = ...  # type: List[Step]
        self.clean_with_zeros = ...  # type: bool
        self.success = ...  # type: bool


class EraseSectors(EraseBasic):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
