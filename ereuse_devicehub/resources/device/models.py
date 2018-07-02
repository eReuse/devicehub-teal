from contextlib import suppress
from operator import attrgetter
from typing import Dict, Set

from ereuse_devicehub.resources.enums import ComputerChassis, DataStorageInterface, DisplayTech, \
    RamFormat, RamInterface
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE, STR_SM_SIZE, Thing
from itertools import chain
from sqlalchemy import BigInteger, Column, Enum as DBEnum, Float, ForeignKey, Integer, Sequence, \
    SmallInteger, Unicode, inspect
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import ColumnProperty, backref, relationship, validates
from sqlalchemy.util import OrderedSet
from sqlalchemy_utils import ColorType
from stdnum import imei, meid
from teal.db import CASCADE, POLYMORPHIC_ID, POLYMORPHIC_ON, ResourceNotFound, check_range
from teal.marshmallow import ValidationError

from ereuse_utils.naming import Naming


class Device(Thing):
    """
    Base class for any type of physical object that can be identified.
    """

    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)
    id.comment = """
        The identifier of the device for this database.
    """
    type = Column(Unicode(STR_SM_SIZE), nullable=False)
    hid = Column(Unicode(STR_BIG_SIZE), unique=True)
    hid.comment = """
        The Hardware ID (HID) is the unique ID traceability systems 
        use to ID a device globally.
    """
    model = Column(Unicode(STR_BIG_SIZE))
    manufacturer = Column(Unicode(STR_SIZE))
    serial_number = Column(Unicode(STR_SIZE))
    weight = Column(Float(decimal_return_scale=3), check_range('weight', 0.1, 3))
    weight.comment = """
        The weight of the device in Kgm.
    """
    width = Column(Float(decimal_return_scale=3), check_range('width', 0.1, 3))
    width.comment = """
        The width of the device in meters.
    """
    height = Column(Float(decimal_return_scale=3), check_range('height', 0.1, 3))
    height.comment = """
        The height of the device in meters.
    """
    depth = Column(Float(decimal_return_scale=3), check_range('depth', 0.1, 3))
    color = Column(ColorType)
    color.comment = """
    
    """

    @property
    def events(self) -> list:
        """
        All the events where the device participated, including
        1) events performed directly to the device, 2) events performed
        to a component, and 3) events performed to a parent device.

        Events are returned by ascending creation time.
        """
        return sorted(chain(self.events_multiple, self.events_one), key=attrgetter('created'))

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        with suppress(TypeError):
            self.hid = Naming.hid(self.manufacturer, self.serial_number, self.model)

    @property
    def physical_properties(self) -> Dict[str, object or None]:
        """
        Fields that describe the physical properties of a device.

        :return A generator where each value is a tuple with tho fields:
                - Column.
                - Actual value of the column or None.
        """
        # todo ensure to remove materialized values when start using them
        # todo or self.__table__.columns if inspect fails
        return {c.key: getattr(self, c.key, None)
                for c in inspect(self.__class__).attrs
                if isinstance(c, ColumnProperty)
                and not getattr(c, 'foreign_keys', None)
                and c.key not in {'id', 'type', 'created', 'updated', 'parent_id', 'hid'}}

    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Device':
            args[POLYMORPHIC_ON] = cls.type
        return args

    def __lt__(self, other):
        return self.id < other.id

    def __repr__(self) -> str:
        return '<{0.t} {0.id!r} model={0.model!r} S/N={0.serial_number!r}>'.format(self)


class DisplayMixin:
    size = Column(Float(decimal_return_scale=2), check_range('size', 2, 150))
    size.comment = """
        The size of the monitor in inches.
    """
    technology = Column(DBEnum(DisplayTech))
    technology.comment = """
        The technology the monitor uses to display the image.
    """
    resolution_width = Column(SmallInteger, check_range('resolution_width', 10, 20000))
    resolution_width.comment = """
        The maximum horizontal resolution the monitor can natively support
        in pixels.
    """
    resolution_height = Column(SmallInteger, check_range('resolution_height', 10, 20000))
    resolution_height.comment = """
        The maximum vertical resolution the monitor can natively support
        in pixels.
    """


class Computer(Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    chassis = Column(DBEnum(ComputerChassis), nullable=False)

    @property
    def events(self) -> list:
        return sorted(chain(super().events, self.events_parent), key=attrgetter('created'))


class Desktop(Computer):
    pass


class Laptop(Computer):
    pass


class Server(Computer):
    pass


class Monitor(DisplayMixin, Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)


class ComputerMonitor(Monitor):
    pass


class TelevisionSet(Monitor):
    pass


class Mobile(Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    imei = Column(BigInteger)
    imei.comment = """
        The International Mobile Equipment Identity of the smartphone
        as an integer.
    """
    meid = Column(Unicode)
    meid.comment = """
        The Mobile Equipment Identifier as a hexadecimal string.
    """

    @validates('imei')
    def validate_imei(self, _, value: int):
        if not imei.is_valid(value):
            raise ValidationError('{} is not a valid imei.'.format(value))

    @validates('meid')
    def validate_meid(self, _, value: str):
        if not meid.is_valid(value):
            raise ValidationError('{} is not a valid meid.'.format(value))


class Smartphone(Mobile):
    pass


class Tablet(Mobile):
    pass


class Cellphone(Mobile):
    pass


class Component(Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)

    parent_id = Column(BigInteger, ForeignKey(Computer.id))
    parent = relationship(Computer,
                          backref=backref('components',
                                          lazy=True,
                                          cascade=CASCADE,
                                          order_by=lambda: Component.id,
                                          collection_class=OrderedSet),
                          primaryjoin=parent_id == Computer.id)

    def similar_one(self, parent: Computer, blacklist: Set[int]) -> 'Component':
        """
        Gets a component that:
        - has the same parent.
        - Doesn't generate HID.
        - Has same physical properties.
        :param parent:
        :param blacklist: A set of components to not to consider
                          when looking for similar ones.
        """
        assert self.hid is None, 'Don\'t use this method with a component that has HID'
        component = self.__class__.query \
            .filter_by(parent=parent, hid=None, **self.physical_properties) \
            .filter(~Component.id.in_(blacklist)) \
            .first()
        if not component:
            raise ResourceNotFound(self.type)
        return component

    @property
    def events(self) -> list:
        return sorted(chain(super().events, self.events_components), key=attrgetter('created'))


class JoinedComponentTableMixin:
    @declared_attr
    def id(cls):
        return Column(BigInteger, ForeignKey(Component.id), primary_key=True)


class GraphicCard(JoinedComponentTableMixin, Component):
    memory = Column(SmallInteger, check_range('memory', min=1, max=10000))
    memory.comment = """
        The amount of memory of the Graphic Card in MB.
    """


class DataStorage(JoinedComponentTableMixin, Component):
    size = Column(Integer, check_range('size', min=1, max=10 ** 8))
    size.comment = """
        The size of the data-storage in MB.
    """
    interface = Column(DBEnum(DataStorageInterface))


class HardDrive(DataStorage):
    pass


class SolidStateDrive(DataStorage):
    pass


class Motherboard(JoinedComponentTableMixin, Component):
    slots = Column(SmallInteger, check_range('slots', min=0))
    slots.comment = """
        PCI slots the motherboard has.
    """
    usb = Column(SmallInteger, check_range('usb', min=0))
    firewire = Column(SmallInteger, check_range('firewire', min=0))
    serial = Column(SmallInteger, check_range('serial', min=0))
    pcmcia = Column(SmallInteger, check_range('pcmcia', min=0))


class NetworkMixin:
    speed = Column(SmallInteger, check_range('speed', min=10, max=10000))
    speed.comment = """
        The maximum speed this network adapter can handle, in mbps.
    """


class NetworkAdapter(JoinedComponentTableMixin, NetworkMixin, Component):
    pass


class Processor(JoinedComponentTableMixin, Component):
    speed = Column(Float, check_range('speed', 0.1, 15))
    cores = Column(SmallInteger, check_range('cores', 1, 10))
    address = Column(SmallInteger, check_range('address', 8, 256))


class RamModule(JoinedComponentTableMixin, Component):
    size = Column(SmallInteger, check_range('size', min=128, max=17000))
    speed = Column(Float, check_range('speed', min=100, max=10000))
    interface = Column(DBEnum(RamInterface))
    format = Column(DBEnum(RamFormat))


class SoundCard(JoinedComponentTableMixin, Component):
    pass


class Display(JoinedComponentTableMixin, DisplayMixin, Component):
    """
    The display of a device. This is used in all devices that have
    displays but that it is not their main treat, like laptops,
    mobiles, smart-watches, and so on; excluding then ComputerMonitor
    and Television Set.
    """
    pass
