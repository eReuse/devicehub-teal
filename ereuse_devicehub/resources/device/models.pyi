from datetime import datetime
from typing import Dict, List, Set, Type, Union

from boltons import urlutils
from boltons.urlutils import URL
from colour import Color
from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship
from teal.db import Model
from teal.enums import Layouts

from ereuse_devicehub.resources.agent.models import Agent
from ereuse_devicehub.resources.device import states
from ereuse_devicehub.resources.enums import ComputerChassis, DataStorageInterface, \
    DataStoragePrivacyCompliance, DisplayTech, PrinterTechnology, RamFormat, RamInterface
from ereuse_devicehub.resources.event import models as e
from ereuse_devicehub.resources.image.models import ImageList
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.tag import Tag


class Device(Thing):
    id = ...  # type: Column
    type = ...  # type: Column
    hid = ...  # type: Column
    model = ...  # type: Column
    manufacturer = ...  # type: Column
    serial_number = ...  # type: Column
    weight = ...  # type: Column
    width = ...  # type: Column
    height = ...  # type: Column
    depth = ...  # type: Column
    color = ...  # type: Column
    lots = ...  # type: relationship
    production_date = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = ...  # type: int
        self.type = ...  # type: str
        self.hid = ...  # type: str
        self.model = ...  # type: str
        self.manufacturer = ...  # type: str
        self.serial_number = ...  # type: str
        self.weight = ...  # type: float
        self.width = ...  # type:float
        self.height = ...  # type: float
        self.depth = ...  # type: float
        self.color = ...  # type: Color
        self.events = ...  # type: List[e.Event]
        self.physical_properties = ...  # type: Dict[str, object or None]
        self.events_multiple = ...  # type: Set[e.EventWithMultipleDevices]
        self.events_one = ...  # type: Set[e.EventWithOneDevice]
        self.images = ...  # type: ImageList
        self.tags = ...  # type: Set[Tag]
        self.lots = ...  # type: Set[Lot]
        self.production_date = ...  # type: datetime

    @property
    def url(self) -> urlutils.URL:
        pass

    @property
    def rate(self) -> Union[e.AggregateRate, None]:
        pass

    @property
    def price(self) -> Union[e.Price, None]:
        pass

    @property
    def trading(self) -> Union[states.Trading, None]:
        pass

    @property
    def physical(self) -> Union[states.Physical, None]:
        pass

    @property
    def physical_possessor(self) -> Union[Agent, None]:
        pass

    def last_event_of(self, *types: Type[e.Event]) -> e.Event:
        pass


class DisplayMixin:
    technology = ...  # type: Column
    size = ...  # type: Column
    resolution_width = ...  # type: Column
    resolution_height = ...  # type: Column
    refresh_rate = ...  # type: Column
    contrast_ratio = ...  # type: Column
    touchable = ...  # type: Column

    def __init__(self) -> None:
        super().__init__()
        self.technology = ...  # type: DisplayTech
        self.size = ...  # type: Integer
        self.resolution_width = ...  # type: int
        self.resolution_height = ...  # type: int
        self.refresh_rate = ...  # type: int
        self.contrast_ratio = ...  # type: int
        self.touchable = ...  # type: bool


class Computer(DisplayMixin, Device):
    components = ...  # type: Column
    chassis = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.components = ...  # type: Set[Component]
        self.events_parent = ...  # type: Set[e.Event]
        self.chassis = ...  # type: ComputerChassis

    @property
    def events(self) -> List:
        pass

    @property
    def ram_size(self) -> int:
        pass

    @property
    def data_storage_size(self) -> int:
        pass

    @property
    def processor_model(self) -> str:
        pass

    @property
    def graphic_card_model(self) -> str:
        pass

    @property
    def network_speeds(self) -> List[int]:
        pass


class Desktop(Computer):
    pass


class Laptop(Computer):
    layout = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.layout = ...  # type: Layouts


class Server(Computer):
    pass


class Monitor(DisplayMixin, Device):
    pass


class ComputerMonitor(Monitor):
    pass


class TelevisionSet(Monitor):
    pass


class Mobile(Device):
    imei = ...  # type: Column
    meid = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.imei = ...  # type: int
        self.meid = ...  # type: str


class Smartphone(Mobile):
    pass


class Tablet(Mobile):
    pass


class Cellphone(Mobile):
    pass


class Component(Device):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.parent_id = ...  # type: int
        self.parent = ...  # type: Computer
        self.events_components = ...  # type: Set[e.Event]

    def similar_one(self, parent: Computer, blacklist: Set[int]) -> 'Component':
        pass


class GraphicCard(Component):
    memory = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.memory = ...  # type: int


class DataStorage(Component):
    size = ...  # type: Column
    interface = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.size = ...  # type: int
        self.interface = ...  # type: DataStorageInterface

    @property
    def privacy(self) -> DataStoragePrivacyCompliance:
        pass


class HardDrive(DataStorage):
    pass


class SolidStateDrive(DataStorage):
    pass


class Motherboard(Component):
    slots = ...  # type: Column
    usb = ...  # type: Column
    firewire = ...  # type: Column
    serial = ...  # type: Column
    pcmcia = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.slots = ...  # type: int
        self.usb = ...  # type: int
        self.firewire = ...  # type: int
        self.serial = ...  # type: int
        self.pcmcia = ...  # type: int


class NetworkMixin:
    speed = ...  # type: Column
    wireless = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.speed = ...  # type: int
        self.wireless = ...  # type: bool


class NetworkAdapter(NetworkMixin, Component):
    pass


class Processor(Component):
    speed = ...  # type: Column
    cores = ...  # type: Column
    address = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.speed = ...  # type: float
        self.cores = ...  # type: int
        self.address = ...  # type: int


class RamModule(Component):
    size = ...  # type: Column
    speed = ...  # type: Column
    interface = ...  # type: Column
    format = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.size = ...  # type: int
        self.speed = ...  # type: float
        self.interface = ...  # type: RamInterface
        self.format = ...  # type: RamFormat


class Display(DisplayMixin, Component):
    pass


class ComputerAccessory(Device):
    pass


class SAI(ComputerAccessory):
    pass


class Keyboard(ComputerAccessory):
    layout = ...  # type: Column

    def __init__(self, layout: Layouts, **kwargs):
        super().__init__(**kwargs)
        self.layout = ...  # type: Layouts


class Mouse(ComputerAccessory):
    pass


class MemoryCardReader(ComputerAccessory):
    pass


class Networking(NetworkMixin, Device):
    pass


class Router(Networking):
    pass


class Switch(Networking):
    pass


class Hub(Networking):
    pass


class WirelessAccessPoint(Networking):
    pass


class Printer(Device):
    wireless = ...  # type: Column
    scanning = ...  # type: Column
    technology = ...  # type: Column
    monochrome = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.wireless = ...  # type: bool
        self.scanning = ...  # type: bool
        self.technology = ...  # type: PrinterTechnology
        self.monochrome = ...  # type: bool


class LabelPrinter(Printer):
    pass


class Sound(Device):
    pass


class Microphone(Sound):
    pass


class Video(Device):
    pass


class VideoScaler(Video):
    pass


class Videoconference(Video):
    pass


class Manufacturer(Model):
    CUSTOM_MANUFACTURERS = ...  # type: set
    name = ...  # type: Column
    url = ...  # type: Column
    logo = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.name = ...  # type: str
        self.url = ...  # type: URL
        self.logo = ...  # type: URL

    @classmethod
    def add_all_to_session(cls, session):
        pass
