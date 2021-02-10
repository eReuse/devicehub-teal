from datetime import date, datetime
from fractions import Fraction
from operator import attrgetter
from typing import Dict, Generator, Iterable, List, Optional, Set, Type, TypeVar

from boltons import urlutils
from boltons.urlutils import URL
from colour import Color
from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship
from teal.db import Model
from teal.enums import Layouts

from ereuse_devicehub.resources.action import models as e
from ereuse_devicehub.resources.agent.models import Agent
from ereuse_devicehub.resources.device import states
from ereuse_devicehub.resources.enums import BatteryTechnology, CameraFacing, ComputerChassis, \
    DataStorageInterface, DisplayTech, PrinterTechnology, RamFormat, RamInterface
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.tag import Tag
from ereuse_devicehub.resources.tag.model import Tags

E = TypeVar('E', bound=e.Action)


class Device(Thing):
    ACTION_SORT_KEY = attrgetter('created')

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
    brand = ...  # type: Column
    generation = ...  # type: Column
    version = ...  # type: Column
    variant = ...  # type: Column
    sku = ...  # type: Column
    image = ...  #type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = ...  # type: int
        self.type = ...  # type: str
        self.hid = ...  # type: Optional[str]
        self.model = ...  # type: Optional[str]
        self.manufacturer = ...  # type: Optional[str]
        self.serial_number = ...  # type: Optional[str]
        self.weight = ...  # type: Optional[float]
        self.width = ...  # type:Optional[float]
        self.height = ...  # type: Optional[float]
        self.depth = ...  # type: Optional[float]
        self.color = ...  # type: Optional[Color]
        self.physical_properties = ...  # type: Dict[str, object or None]
        self.actions_multiple = ...  # type: Set[e.ActionWithMultipleDevices]
        self.actions_one = ...  # type: Set[e.ActionWithOneDevice]
        self.tags = ...  # type: Tags[Tag]
        self.lots = ...  # type: Set[Lot]
        self.production_date = ...  # type: Optional[datetime]
        self.brand = ...  # type: Optional[str]
        self.generation = ...  # type: Optional[int]
        self.version = ...  # type: Optional[str]
        self.variant = ...  # type: Optional[str]
        self.sku = ...  # type: Optional[str]
        self.image = ...  # type: Optional[urlutils.URL]

    @property
    def actions(self) -> List[e.Action]:
        pass

    @property
    def problems(self) -> List[e.Action]:
        pass

    @property
    def url(self) -> urlutils.URL:
        pass

    @property
    def rate(self) -> Optional[e.Rate]:
        pass

    @property
    def price(self) -> Optional[e.Price]:
        pass

    @property
    def trading(self) -> Optional[states.Trading]:
        pass

    @property
    def physical(self) -> Optional[states.Physical]:
        pass

    @property
    def physical_possessor(self) -> Optional[Agent]:
        pass

    @property
    def working(self) -> List[e.Test]:
        pass

    def last_action_of(self, *types: Type[E]) -> E:
        pass

    def _warning_actions(self, actions: Iterable[e.Action]) -> Generator[e.Action]:
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
        self.refresh_rate = ...  # type: Optional[int]
        self.contrast_ratio = ...  # type: Optional[int]
        self.touchable = ...  # type: Optional[bool]
        self.aspect_ratio = ...  #type: Fraction
        self.widescreen = ...  # type: bool


class Computer(DisplayMixin, Device):
    components = ...  # type: Column
    chassis = ...  # type: Column
    amount = ...  # type: Column
    owner_address = ...  # type: Column
    transfer_state = ...  # type: Column
    receiver_id = ...  # uuid: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.components = ...  # type: Set[Component]
        self.actions_parent = ...  # type: Set[e.Action]
        self.chassis = ...  # type: ComputerChassis
        self.owner_address = ...  # type: UUID
        self.transfer_state = ...
        self.receiver_address = ...  # type: str

    @property
    def actions(self) -> List:
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

    @property
    def privacy(self) -> Set[e.EraseBasic]:
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
    ram_size = ...  # type: Column
    data_storage_size = ...  # type: Column
    display_size = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.imei = ...  # type: Optional[int]
        self.meid = ...  # type: Optional[str]
        self.ram_size = ...  # type: Optional[int]
        self.data_storage_size = ...  # type: Optional[int]
        self.display_size = ...  # type: Optional[float]


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
        self.actions_components = ...  # type: Set[e.Action]

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
    def privacy(self) -> Optional[e.EraseBasic]:
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
    bios_date = ...  # type: Column
    ram_slots = ...  # type: Column
    ram_max_size = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.slots = ...  # type: int
        self.usb = ...  # type: int
        self.firewire = ...  # type: int
        self.serial = ...  # type: int
        self.pcmcia = ...  # type: int
        self.bios_date = ...  # type: Optional[date]
        self.ram_slots = ...  # type: Optional[int]
        self.ram_max_size = ...  # type: Optional[int]


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
    threads = ...  # type: Column
    abi = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.speed = ...  # type: Optional[float]
        self.cores = ...  # type: Optional[int]
        self.threads = ...  # type: Optional[int]
        self.address = ...  # type: Optional[int]
        self.abi = ...  # type: Optional[str]


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


class SoundCard(Component):
    pass


class Display(DisplayMixin, Component):
    pass


class Battery(Component):
    wireless = ...  # type: Column
    technology = ...  # type: Column
    size = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.wireless = ...  # type: Optional[bool]
        self.technology = ...  # type: Optional[BatteryTechnology]
        self.size = ...  # type: bool


class Camera(Component):
    focal_length = ...  # type: Column
    video_height = ...  # type: Column
    video_width = ...  # type: Column
    horizontal_view_angle = ...  # type: Column
    facing = ...  # type: Column
    vertical_view_angle = ...  # type: Column
    video_stabilization = ...  # type: Column
    flash = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        focal_length = ...  # type: Optional[int]
        video_height = ...  # type: Optional[int]
        video_width = ...  # type: Optional[int]
        horizontal_view_angle = ...  # type: Optional[int]
        facing = ...  # type: Optional[CameraFacing]
        vertical_view_angle = ...  # type: Optional[int]
        video_stabilization = ...  # type: Optional[bool]
        flash = ...  # type: Optional[bool]


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


class Cooking(Device):
    pass


class Mixer(Cooking):
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
