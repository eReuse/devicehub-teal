import csv
import pathlib
from contextlib import suppress
from itertools import chain
from operator import attrgetter
from typing import Dict, List, Set

from boltons import urlutils
from citext import CIText
from ereuse_utils.naming import Naming
from sqlalchemy import BigInteger, Boolean, Column, Enum as DBEnum, Float, ForeignKey, Integer, \
    Sequence, SmallInteger, Unicode, inspect, text
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import ColumnProperty, backref, relationship, validates
from sqlalchemy.util import OrderedSet
from sqlalchemy_utils import ColorType
from stdnum import imei, meid
from teal.db import CASCADE, POLYMORPHIC_ID, POLYMORPHIC_ON, ResourceNotFound, URL, check_lower, \
    check_range
from teal.marshmallow import ValidationError
from teal.resource import url_for_resource

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.enums import ComputerChassis, DataStorageInterface, \
    DataStoragePrivacyCompliance, DisplayTech, RamFormat, RamInterface
from ereuse_devicehub.resources.models import STR_SM_SIZE, Thing


class Device(Thing):
    """
    Base class for any type of physical object that can be identified.
    """

    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)
    id.comment = """
        The identifier of the device for this database.
    """
    type = Column(Unicode(STR_SM_SIZE), nullable=False)
    hid = Column(Unicode(), check_lower('hid'), unique=True)
    hid.comment = """
        The Hardware ID (HID) is the unique ID traceability systems 
        use to ID a device globally.
    """
    model = Column(Unicode(), check_lower('model'))
    manufacturer = Column(Unicode(), check_lower('manufacturer'))
    serial_number = Column(Unicode(), check_lower('serial_number'))
    weight = Column(Float(decimal_return_scale=3), check_range('weight', 0.1, 5))
    weight.comment = """
        The weight of the device in Kgm.
    """
    width = Column(Float(decimal_return_scale=3), check_range('width', 0.1, 5))
    width.comment = """
        The width of the device in meters.
    """
    height = Column(Float(decimal_return_scale=3), check_range('height', 0.1, 5))
    height.comment = """
        The height of the device in meters.
    """
    depth = Column(Float(decimal_return_scale=3), check_range('depth', 0.1, 5))
    depth.comment = """
        The depth of the device in meters.
    """
    color = Column(ColorType)
    color.comment = """The predominant color of the device."""

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

    @property
    def url(self) -> urlutils.URL:
        """The URL where to GET this device."""
        return urlutils.URL(url_for_resource(Device, item_id=self.id))

    @property
    def rate(self):
        """The last AggregateRate of the device."""
        with suppress(LookupError, ValueError):
            from ereuse_devicehub.resources.event.models import AggregateRate
            return self.last_event_of(AggregateRate)

    @property
    def price(self):
        """The actual Price of the device, or None if no price has
        ever been set."""
        with suppress(LookupError, ValueError):
            from ereuse_devicehub.resources.event.models import Price
            return self.last_event_of(Price)

    @property
    def trading(self):
        """The actual trading state, or None if no Trade event has
        ever been performed to this device."""
        from ereuse_devicehub.resources.device import states
        with suppress(LookupError, ValueError):
            event = self.last_event_of(*states.Trading.events())
            return states.Trading(event.__class__)

    @property
    def physical(self):
        """The actual physical state, None otherwise."""
        from ereuse_devicehub.resources.device import states
        with suppress(LookupError, ValueError):
            event = self.last_event_of(*states.Physical.events())
            return states.Physical(event.__class__)

    @property
    def physical_possessor(self):
        """The actual physical possessor or None.

        The physical possessor is the Agent that has physically
        the device. It differs from legal owners, usufructuarees
        or reserves in that the physical possessor does not have
        a legal relation per se with the device, but it is the one
        that has it physically. As an example, a transporter could
        be a physical possessor of a device although it does not
        own it legally.
        """
        from ereuse_devicehub.resources.event.models import Receive
        with suppress(LookupError):
            event = self.last_event_of(Receive)
            return event.agent

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

    def last_event_of(self, *types):
        """Gets the last event of the given types.

        :raise LookupError: Device has not an event of the given type.
        """
        try:
            return next(e for e in reversed(self.events) if isinstance(e, types))
        except StopIteration:
            raise LookupError('{!r} does not contain events of types {}.'.format(self, types))

    def __lt__(self, other):
        return self.id < other.id

    def __str__(self) -> str:
        return '{0.t} {0.id}: model {0.model}, S/N {0.serial_number}'.format(self)

    def __format__(self, format_spec):
        if not format_spec:
            return super().__format__(format_spec)
        v = ''
        if 't' in format_spec:
            v += '{0.t} {0.model}'.format(self)
        if 's' in format_spec:
            v += '({0.manufacturer})'.format(self)
            if self.serial_number:
                v += ' S/N ' + self.serial_number.upper()
        return v


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

    def __format__(self, format_spec: str) -> str:
        v = ''
        if 't' in format_spec:
            v += '{0.t} {0.model}'.format(self)
        if 's' in format_spec:
            v += '({0.manufacturer}) S/N {0.serial_number} – {0.size}in {0.technology}'
        return v


class Computer(Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    chassis = Column(DBEnum(ComputerChassis), nullable=False)

    @property
    def events(self) -> list:
        return sorted(chain(super().events, self.events_parent), key=attrgetter('created'))

    @property
    def ram_size(self) -> int:
        """The total of RAM memory the computer has."""
        return sum(ram.size or 0 for ram in self.components if isinstance(ram, RamModule))

    @property
    def data_storage_size(self) -> int:
        """The total of data storage the computer has."""
        return sum(ds.size or 0 for ds in self.components if isinstance(ds, DataStorage))

    @property
    def processor_model(self) -> str:
        """The model of one of the processors of the computer."""
        return next((p.model for p in self.components if isinstance(p, Processor)), None)

    @property
    def graphic_card_model(self) -> str:
        """The model of one of the graphic cards of the computer."""
        return next((p.model for p in self.components if isinstance(p, GraphicCard)), None)

    @property
    def network_speeds(self) -> List[int]:
        """Returns two values representing the speeds of the network
        adapters of the device.

        1. The max Ethernet speed of the computer, 0 if ethernet
           adaptor exists but its speed is unknown, None if no eth
           adaptor exists.
        2. The max WiFi speed of the computer, 0 if computer has
           WiFi but its speed is unknown, None if no WiFi adaptor
           exists.
        """
        speeds = [None, None]
        for net in (c for c in self.components if isinstance(c, NetworkAdapter)):
            speeds[net.wireless] = max(net.speed or 0, speeds[net.wireless] or 0)
        return speeds

    def __format__(self, format_spec):
        if not format_spec:
            return super().__format__(format_spec)
        v = ''
        if 't' in format_spec:
            v += '{0.chassis} {0.model}'.format(self)
        elif 's' in format_spec:
            v += '({0.manufacturer})'.format(self)
            if self.serial_number:
                v += ' S/N ' + self.serial_number.upper()
        return v


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
        if not imei.is_valid(str(value)):
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

    @property
    def privacy(self):
        """Returns the privacy compliance state of the data storage."""
        # todo add physical destruction event
        from ereuse_devicehub.resources.event.models import EraseBasic
        with suppress(LookupError):
            erase = self.last_event_of(EraseBasic)
            return DataStoragePrivacyCompliance.from_erase(erase)

    def __format__(self, format_spec):
        v = super().__format__(format_spec)
        if 's' in format_spec:
            v += ' – {} GB'.format(self.size // 1000)
        return v


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
    wireless = Column(Boolean, nullable=False, default=False)
    wireless.comment = """
        Whether it is a wireless interface.
    """

    def __format__(self, format_spec):
        v = super().__format__(format_spec)
        if 's' in format_spec:
            v += ' – {} Mbps'.format(self.speed)
        return v


class NetworkAdapter(JoinedComponentTableMixin, NetworkMixin, Component):
    pass


class Processor(JoinedComponentTableMixin, Component):
    speed = Column(Float, check_range('speed', 0.1, 15))
    cores = Column(SmallInteger, check_range('cores', 1, 10))
    threads = Column(SmallInteger, check_range('threads', 1, 20))
    address = Column(SmallInteger, check_range('address', 8, 256))


class RamModule(JoinedComponentTableMixin, Component):
    size = Column(SmallInteger, check_range('size', min=128, max=17000))
    speed = Column(SmallInteger, check_range('speed', min=100, max=10000))
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


class Manufacturer(db.Model):
    __table_args__ = {'schema': 'common'}
    CSV_DELIMITER = csv.get_dialect('excel').delimiter

    name = db.Column(CIText(),
                     primary_key=True,
                     # from https://niallburkley.com/blog/index-columns-for-like-in-postgres/
                     index=db.Index('name', text('name gin_trgm_ops'), postgresql_using='gin'))
    url = db.Column(URL(), unique=True)
    logo = db.Column(URL())

    @classmethod
    def add_all_to_session(cls, session: db.Session):
        """Adds all manufacturers to session."""
        cursor = session.connection().connection.cursor()
        #: Dialect used to write the CSV

        with pathlib.Path(__file__).parent.joinpath('manufacturers.csv').open() as f:
            cursor.copy_expert(
                'COPY common.manufacturer FROM STDIN (FORMAT csv)',
                f
            )
