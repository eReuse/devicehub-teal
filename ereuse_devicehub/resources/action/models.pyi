import ipaddress
from datetime import datetime, timedelta
from decimal import Decimal
from distutils.version import StrictVersion
from typing import Dict, List, Optional, Set, Tuple, Union
from uuid import UUID

from boltons import urlutils
from boltons.urlutils import URL
from sqlalchemy import Column
from sqlalchemy.orm import relationship
from sqlalchemy_utils import Currency
from teal import enums
from teal.db import Model
from teal.enums import Country

from ereuse_devicehub.resources.agent.models import Agent
from ereuse_devicehub.resources.device.models import Component, Computer, Device
from ereuse_devicehub.resources.enums import AppearanceRange, BatteryHealth, ErasureStandards, \
    FunctionalityRange, PhysicalErasureMethod, PriceSoftware, RatingRange, ReceiverRole, Severity, \
    SnapshotSoftware, TestDataStorageLength
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import User


class Action(Thing):
    id = ...  # type: Column
    name = ...  # type: Column
    type = ...  # type: Column
    description = ...  # type: Column
    snapshot_id = ...  # type: Column
    snapshot = ...  # type: relationship
    author_id = ...  # type: Column
    agent = ...  # type: relationship
    components = ...  # type: relationship
    parent_id = ...  # type: Column
    parent = ...  # type: relationship
    closed = ...  # type: Column
    start_time = ...  # type: Column
    end_time = ...  # type: Column
    agent_id = ...  # type: Column
    severity = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = ...  # type: UUID
        self.name = ...  # type: str
        self.type = ...  # type: str
        self.closed = ...  # type: bool
        self.description = ...  # type: str
        self.start_time = ...  # type: datetime
        self.end_time = ...  # type: datetime
        self.snapshot = ...  # type: Snapshot
        self.components = ...  # type: Set[Component]
        self.parent = ...  # type: Computer
        self.agent = ...  # type: Agent
        self.author = ...  # type: User
        self.severity = ...  # type: Severity

    @property
    def url(self) -> urlutils.URL:
        pass

    @property
    def elapsed(self) -> timedelta:
        pass

    @property
    def certificate(self) -> Optional[urlutils.URL]:
        return None

    @property
    def date_str(self):
        return '{:%c}'.format(self.end_time or self.created)


class ActionWithOneDevice(Action):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.device = ...  # type: Device


class ActionWithMultipleDevices(Action):
    devices = ...  # type: relationship

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.devices = ...  # type: Set[Device]


class Add(ActionWithOneDevice):
    pass


class Remove(ActionWithOneDevice):
    pass


class Step(Model):
    type = ...  # type: Column
    num = ...  # type: Column
    start_time = ...  # type: Column
    end_time = ...  # type: Column
    erasure = ...  # type: relationship
    severity = ...  # type: Column

    def __init__(self, num=None, success=None, start_time=None, end_time=None,
                 erasure=None, severity=None) -> None:
        self.type = ...  # type: str
        self.num = ...  # type: int
        self.start_time = ...  # type: datetime
        self.end_time = ...  # type: datetime
        self.erasure = ...  # type: EraseBasic
        self.severity = ...  # type: Severity


class StepZero(Step):
    pass


class StepRandom(Step):
    pass


class EraseBasic(ActionWithOneDevice):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.start_time = ...  # type: datetime
        self.end_time = ...  # type: datetime
        self.steps = ...  # type: List[Step]
        self.zeros = ...  # type: bool
        self.success = ...  # type: bool

    @property
    def standards(self) -> Set[ErasureStandards]:
        pass

    @property
    def certificate(self) -> urlutils.URL:
        pass


class EraseSectors(EraseBasic):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class ErasePhysical(EraseBasic):
    method = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.method = ...  # type: PhysicalErasureMethod


class Snapshot(ActionWithOneDevice):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.uuid = ...  # type: UUID
        self.version = ...  # type: StrictVersion
        self.software = ...  # type: SnapshotSoftware
        self.elapsed = ...  # type: timedelta
        self.device = ...  # type: Computer
        self.actions = ...  # type: Set[Action]


class Install(ActionWithOneDevice):
    name = ...  # type: Column
    elapsed = ...  # type: Column
    address = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = ...  # type: str
        self.elapsed = ...  # type: timedelta
        self.address = ...  # type: Optional[int]


class SnapshotRequest(Model):
    def __init__(self, **kwargs) -> None:
        self.id = ...  # type: UUID
        self.request = ...  # type: dict
        self.snapshot = ...  # type: Snapshot


class Benchmark(ActionWithOneDevice):
    pass


class BenchmarkDataStorage(Benchmark):
    read_speed = ...  # type: Column
    write_speed = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.read_speed = ...  # type: float
        self.write_speed = ...  # type: float


class BenchmarkWithRate(Benchmark):
    rate = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.rate = ...  # type: int


class BenchmarkProcessor(BenchmarkWithRate):
    pass


class BenchmarkProcessorSysbench(BenchmarkProcessor):
    pass


class BenchmarkRamSysbench(BenchmarkWithRate):
    pass


class BenchmarkGraphicCard(BenchmarkWithRate):
    pass


class Test(ActionWithOneDevice):
    elapsed = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.elapsed = ...  # type: Optional[timedelta]
        self.success = ...  # type: bool


class MeasureBattery(Test):
    size = ...  # type: Column
    voltage = ...  # type: Column
    cycle_count = ...  # type: Column
    health = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.size = ...  # type: int
        self.voltage = ...  # type: int
        self.cycle_count = ...  # type: Optional[int]
        self.health = ...  # type: Optional[BatteryHealth]


class TestDataStorage(Test):
    length = ...  # type: Column
    status = ...  # type: Column
    lifetime = ...  # type: Column
    first_error = ...  # type: Column
    passed_lifetime = ...  # type: Column
    assessment = ...  # type: Column
    reallocated_sector_count = ...  # type: Column
    power_cycle_count = ...  # type: Column
    reported_uncorrectable_errors = ...  # type: Column
    command_timeout = ...  # type: Column
    current_pending_sector_count = ...  # type: Column
    offline_uncorrectable = ...  # type: Column
    remaining_lifetime_percentage = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = ...  # type: UUID
        self.length = ...  # type: TestDataStorageLength
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


class TestAudio(Test):
    """
    Test to check all this aspects related with audio functions, Manual Tests??
    """
    _speaker = ...  # type: Column
    _microphone = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.speaker = ...  # type: bool
        self.microphone = ...  # type: bool


class TestConnectivity(Test):
    pass


class TestCamera(Test):
    pass


class TestKeyboard(Test):
    pass


class TestTrackpad(Test):
    pass


class TestBios(Test):
    bios_power_on = ...  # type: Column
    access_range = ...  # type: Column


class VisualTest(Test):
    appearance_range = ...  # type: Column
    functionality_range = ...  # type: Column
    labelling = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.appearance_range = ...  # type: AppearanceRange
        self.functionality_range = ...  # type: FunctionalityRange
        self.labelling = ...  # type: Optional[bool]


class Rate(ActionWithOneDevice):
    N = 2
    _rating = ...  # type: Column
    _appearance = ...  # type: Column
    _functionality = ...  # type: Column
    version = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.rating = ...  # type: float
        self.version = ...  # type: StrictVersion
        self.appearance = ...  # type: float
        self.functionality = ...  # type: float

    @property
    def rating_range(self) -> RatingRange:
        pass


class RateComputer(Rate):
    _processor = ...  # type: Column
    _ram = ...  # type: Column
    _data_storage = ...  # type: Column
    _graphic_card = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.processor = ...  # type: Optional[float]
        self.ram = ...  # type: Optional[float]
        self.data_storage = ...  # type: Optional[float]
        self.graphic_card = ...  # type: Optional[float]

    @classmethod
    def compute(cls, device: Device) -> Tuple[RateComputer, EreusePrice]:
        pass

    @property
    def data_storage_range(self) -> Optional[RatingRange]:
        pass

    @property
    def ram_range(self) -> Optional[RatingRange]:
        pass

    @property
    def processor_range(self) -> Optional[RatingRange]:
        pass

    @property
    def graphic_card_range(self) -> Optional[RatingRange]:
        pass


class Price(ActionWithOneDevice):
    SCALE = ...
    ROUND = ...
    currency = ...  # type: Column
    price = ...  # type: Column
    software = ...  # type: Column
    version = ...  # type: Column
    rating_id = ...  # type: Column
    rating = ...  # type: relationship

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.price = ...  # type: Decimal
        self.currency = ...  # type: Currency
        self.software = ...  # type: PriceSoftware
        self.version = ...  # type: StrictVersion
        self.rating = ...  # type: Rate

    @classmethod
    def to_price(cls, value: Union[Decimal, float], rounding=ROUND) -> Decimal:
        pass


class EreusePrice(Price):
    MULTIPLIER = ...  # type: Dict

    class Type:
        def __init__(self, percentage, price) -> None:
            super().__init__()
            self.amount = ...  # type: float
            self.percentage = ...  # type: float

    class Service:
        def __init__(self) -> None:
            super().__init__()
            self.standard = ...  # type: EreusePrice.Type
            self.warranty2 = ...  # type: EreusePrice.Type

    def __init__(self, rating: Rate, **kwargs) -> None:
        super().__init__(**kwargs)
        self.retailer = ...  # type: EreusePrice.Service
        self.platform = ...  # type: EreusePrice.Service
        self.refurbisher = ...  # type: EreusePrice.Service
        self.warranty2 = ...  # type: float


class ToRepair(ActionWithMultipleDevices):
    pass


class Repair(ActionWithMultipleDevices):
    pass


class Ready(ActionWithMultipleDevices):
    pass


class ToPrepare(ActionWithMultipleDevices):
    pass


class Prepare(ActionWithMultipleDevices):
    pass


class Live(ActionWithOneDevice):
    serial_number = ...  # type: Column
    time = ...  # type: Column


class Organize(ActionWithMultipleDevices):
    pass


class Reserve(Organize):
    pass


class Trade(ActionWithMultipleDevices):
    shipping_date = ...  # type: Column
    invoice_number = ...  # type: Column
    price = ...  # type: relationship
    to = ...  # type: relationship
    confirms = ...  # type: relationship

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.shipping_date = ...  # type: datetime
        self.invoice_number = ...  # type: str
        self.price = ...  # type: Price
        self.to = ...  # type: Agent
        self.confirms = ...  # type: Organize


class InitTransfer(Trade):
    pass


class Sell(Trade):
    pass


class Donate(Trade):
    pass


class Rent(Trade):
    pass


class MakeAvailable(ActionWithMultipleDevices):
    pass


class CancelTrade(Trade):
    pass


class ToDisposeProduct(Trade):
    pass


class DisposeProduct(Trade):
    pass


class TransferOwnershipBlockchain(Trade):
    pass
    
    
class Allocate(ActionWithMultipleDevices):
    code = ...  # type: Column
    end_users = ...  # type: Column

    
class Deallocate(ActionWithMultipleDevices):
    code = ...  # type: Column


class Migrate(ActionWithMultipleDevices):
    other = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.other = ...  # type: URL


class MigrateTo(Migrate):
    pass


class MigrateFrom(Migrate):
    pass
