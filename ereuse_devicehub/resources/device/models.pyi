from typing import Dict, List, Set

from colour import Color
from sqlalchemy import Column, Integer

from ereuse_devicehub.resources.enums import ComputerChassis, DataStorageInterface, DisplayTech, \
    RamFormat, RamInterface
from ereuse_devicehub.resources.event.models import Event, EventWithMultipleDevices, \
    EventWithOneDevice
from ereuse_devicehub.resources.image.models import ImageList
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
        self.events = ...  # type: List[Event]
        self.physical_properties = ...  # type: Dict[str, object or None]
        self.events_multiple = ...  # type: Set[EventWithMultipleDevices]
        self.events_one = ...  # type: Set[EventWithOneDevice]
        self.images = ...  # type: ImageList
        self.tags = ...  # type: Set[Tag]


class DisplayMixin:
    technology = ...  # type: Column
    size = ...  # type: Column
    resolution_width = ...  # type: Column
    resolution_height = ...  # type: Column

    def __init__(self) -> None:
        super().__init__()
        self.technology = ...  # type: DisplayTech
        self.size = ...  # type: Integer
        self.resolution_width = ...  # type: int
        self.resolution_height = ...  # type: int


class Computer(DisplayMixin, Device):
    components = ...  # type: Column
    chassis = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.components = ...  # type: Set[Component]
        self.events_parent = ...  # type: Set[Event]
        self.chassis = ...  # type: ComputerChassis


class Desktop(Computer):
    pass


class Laptop(Computer):
    pass


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
        self.events_components = ...  # type: Set[Event]

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


class NetworkAdapter(Component):
    speed = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.speed = ...  # type: int


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
