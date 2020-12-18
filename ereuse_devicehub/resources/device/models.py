import pathlib
from contextlib import suppress
from fractions import Fraction
from itertools import chain
from operator import attrgetter
from typing import Dict, List, Set

from boltons import urlutils
from citext import CIText
from ereuse_utils.naming import HID_CONVERSION_DOC, Naming
from flask import g
from more_itertools import unique_everseen
from sqlalchemy import BigInteger, Boolean, Column, Enum as DBEnum, Float, ForeignKey, Integer, \
    Sequence, SmallInteger, Unicode, inspect, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import ColumnProperty, backref, relationship, validates
from sqlalchemy.util import OrderedSet
from sqlalchemy_utils import ColorType
from stdnum import imei, meid
from teal.db import CASCADE_DEL, POLYMORPHIC_ID, POLYMORPHIC_ON, ResourceNotFound, URL, \
    check_lower, check_range, IntEnum
from teal.enums import Layouts
from teal.marshmallow import ValidationError
from teal.resource import url_for_resource

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.enums import BatteryTechnology, CameraFacing, ComputerChassis, \
    DataStorageInterface, DisplayTech, PrinterTechnology, RamFormat, RamInterface, Severity, TransferState
from ereuse_devicehub.resources.models import STR_SM_SIZE, Thing, listener_reset_field_updated_in_actual_time
from ereuse_devicehub.resources.user.models import User



class Device(Thing):
    """Base class for any type of physical object that can be identified.

    Device partly extends `Schema's IndividualProduct <https
    ://schema.org/IndividualProduct>`_, adapting it to our
    use case.

    A device requires an identification method, ideally a serial number,
    although it can be identified only with tags too. More ideally
    both methods are used.

    Devices can contain ``Components``, which are just a type of device
    (it is a recursive relationship).
    """
    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)
    id.comment = """The identifier of the device for this database. Used only
    internally for software; users should not use this.
    """
    type = Column(Unicode(STR_SM_SIZE), nullable=False)
    hid = Column(Unicode(), check_lower('hid'), unique=False)
    hid.comment = """The Hardware ID (HID) is the ID traceability
    systems use to ID a device globally. This field is auto-generated
    from Devicehub using literal identifiers from the device,
    so it can re-generated *offline*.
    """ + HID_CONVERSION_DOC
    model = Column(Unicode(), check_lower('model'))
    model.comment = """The model of the device in lower case.

    The model is the unambiguous, as technical as possible, denomination
    for the product. This field, among others, is used to identify
    the product.
    """
    manufacturer = Column(Unicode(), check_lower('manufacturer'))
    manufacturer.comment = """The normalized name of the manufacturer,
    in lower case.

    Although as of now Devicehub does not enforce normalization,
    users can choose a list of normalized manufacturer names
    from the own ``/manufacturers`` REST endpoint.
    """
    serial_number = Column(Unicode(), check_lower('serial_number'))
    serial_number.comment = """The serial number of the device in lower case."""
    brand = db.Column(CIText())
    brand.comment = """A naming for consumers. This field can represent
    several models, so it can be ambiguous, and it is not used to
    identify the product.
    """
    generation = db.Column(db.SmallInteger, check_range('generation', 0))
    generation.comment = """The generation of the device."""
    version = db.Column(db.CIText())
    version.comment = """The version code of this device, like v1 or A001."""
    weight = Column(Float(decimal_return_scale=4), check_range('weight', 0.1, 5))
    weight.comment = """The weight of the device in Kg."""
    width = Column(Float(decimal_return_scale=4), check_range('width', 0.1, 5))
    width.comment = """The width of the device in meters."""
    height = Column(Float(decimal_return_scale=4), check_range('height', 0.1, 5))
    height.comment = """The height of the device in meters."""
    depth = Column(Float(decimal_return_scale=4), check_range('depth', 0.1, 5))
    depth.comment = """The depth of the device in meters."""
    color = Column(ColorType)
    color.comment = """The predominant color of the device."""
    production_date = Column(db.DateTime)
    production_date.comment = """The date of production of the device.
    This is timezone naive, as Workbench cannot report this data with timezone information.
    """
    variant = Column(db.CIText())
    variant.comment = """A variant or sub-model of the device."""
    sku = db.Column(db.CIText())
    sku.comment = """The Stock Keeping Unit (SKU), i.e. a
    merchant-specific identifier for a product or service.
    """
    image = db.Column(db.URL)
    image.comment = "An image of the device."

    owner_id = db.Column(UUID(as_uuid=True),
                         db.ForeignKey(User.id),
                         nullable=False,
                         default=lambda: g.user.id)
    owner = db.relationship(User, primaryjoin=owner_id == User.id)
    allocated = db.Column(Boolean, default=False)
    allocated.comment = "device is allocated or not."

    _NON_PHYSICAL_PROPS = {
        'id',
        'type',
        'created',
        'updated',
        'parent_id',
        'owner_id',
        'hid',
        'production_date',
        'color',  # these are only user-input thus volatile
        'width',
        'height',
        'depth',
        'weight',
        'brand',
        'generation',
        'production_date',
        'variant',
        'version',
        'sku',
        'image',
        'allocated'
    }

    __table_args__ = (
        db.Index('device_id', id, postgresql_using='hash'),
        db.Index('type_index', type, postgresql_using='hash')
    )

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self.set_hid()

    @property
    def actions(self) -> list:
        """All the actions where the device participated, including:

        1. Actions performed directly to the device.
        2. Actions performed to a component.
        3. Actions performed to a parent device.

        Actions are returned by descending ``created`` time.
        """
        return sorted(chain(self.actions_multiple, self.actions_one), key=lambda x: x.created)

    @property
    def problems(self):
        """Current actions with severity.Warning or higher.

        There can be up to 3 actions: current Snapshot,
        current Physical action, current Trading action.
        """
        from ereuse_devicehub.resources.device import states
        from ereuse_devicehub.resources.action.models import Snapshot
        actions = set()
        with suppress(LookupError, ValueError):
            actions.add(self.last_action_of(Snapshot))
        with suppress(LookupError, ValueError):
            actions.add(self.last_action_of(*states.Physical.actions()))
        with suppress(LookupError, ValueError):
            actions.add(self.last_action_of(*states.Trading.actions()))
        return self._warning_actions(actions)

    @property
    def physical_properties(self) -> Dict[str, object or None]:
        """Fields that describe the physical properties of a device.

        :return A dictionary:
                - Column.
                - Actual value of the column or None.
        """
        # todo ensure to remove materialized values when start using them
        # todo or self.__table__.columns if inspect fails
        return {c.key: getattr(self, c.key, None)
                for c in inspect(self.__class__).attrs
                if isinstance(c, ColumnProperty)
                and not getattr(c, 'foreign_keys', None)
                and c.key not in self._NON_PHYSICAL_PROPS}

    @property
    def url(self) -> urlutils.URL:
        """The URL where to GET this device."""
        return urlutils.URL(url_for_resource(Device, item_id=self.id))

    @property
    def rate(self):
        """The last Rate of the device."""
        with suppress(LookupError, ValueError):
            from ereuse_devicehub.resources.action.models import Rate
            return self.last_action_of(Rate)

    @property
    def price(self):
        """The actual Price of the device, or None if no price has
        ever been set."""
        with suppress(LookupError, ValueError):
            from ereuse_devicehub.resources.action.models import Price
            return self.last_action_of(Price)

    @property
    def trading(self):
        """The actual trading state, or None if no Trade action has
        ever been performed to this device."""
        from ereuse_devicehub.resources.device import states
        with suppress(LookupError, ValueError):
            action = self.last_action_of(*states.Trading.actions())
            return states.Trading(action.__class__)

    @property
    def physical(self):
        """The actual physical state, None otherwise."""
        from ereuse_devicehub.resources.device import states
        with suppress(LookupError, ValueError):
            action = self.last_action_of(*states.Physical.actions())
            return states.Physical(action.__class__)

    @property
    def traking(self):
        """The actual traking state, None otherwise."""
        from ereuse_devicehub.resources.device import states
        with suppress(LookupError, ValueError):
            action = self.last_action_of(*states.Traking.actions())
            return states.Traking(action.__class__)

    @property
    def usage(self):
        """The actual usage state, None otherwise."""
        from ereuse_devicehub.resources.device import states
        with suppress(LookupError, ValueError):
            action = self.last_action_of(*states.Usage.actions())
            return states.Usage(action.__class__)

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

        Note that there can only be one physical possessor per device,
        and :class:`ereuse_devicehub.resources.action.models.Receive`
        changes it.
        """
        pass
        # TODO @cayop uncomment this lines for link the possessor with the device
        # from ereuse_devicehub.resources.action.models import Receive
        # with suppress(LookupError):
            # action = self.last_action_of(Receive)
            # return action.agent_to

    @property
    def working(self):
        """A list of the current tests with warning or errors. A
        device is working if the list is empty.

        This property returns, for the last test performed of each type,
        the one with the worst ``severity`` of them, or ``None`` if no
        test has been executed.
        """
        from ereuse_devicehub.resources.action.models import Test
        current_tests = unique_everseen((e for e in reversed(self.actions) if isinstance(e, Test)),
                                        key=attrgetter('type'))  # last test of each type
        return self._warning_actions(current_tests)

    @declared_attr
    def __mapper_args__(cls):
        """Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Device':
            args[POLYMORPHIC_ON] = cls.type
        return args

    def set_hid(self):
        with suppress(TypeError):
            self.hid = Naming.hid(self.type, self.manufacturer, self.model, self.serial_number)

    def last_action_of(self, *types):
        """Gets the last action of the given types.

        :raise LookupError: Device has not an action of the given type.
        """
        try:
            # noinspection PyTypeHints
            actions = self.actions
            actions.sort(key=lambda x: x.created)
            return next(e for e in reversed(actions) if isinstance(e, types))
        except StopIteration:
            raise LookupError('{!r} does not contain actions of types {}.'.format(self, types))

    def _warning_actions(self, actions):
        return sorted(ev for ev in actions if ev.severity >= Severity.Warning)

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
            superclass = self.__class__.mro()[1]
            if not isinstance(self, Device) and superclass != Device:
                assert issubclass(superclass, Thing)
                v += superclass.__name__ + ' '
            v += '{0.manufacturer}'.format(self)
            if self.serial_number:
                v += ' ' + self.serial_number.upper()
        return v


class DisplayMixin:
    """Base class for the Display Component and the Monitor Device."""
    size = Column(Float(decimal_return_scale=1), check_range('size', 2, 150), nullable=True)
    size.comment = """The size of the monitor in inches."""
    technology = Column(DBEnum(DisplayTech))
    technology.comment = """The technology the monitor uses to display
    the image.
    """
    resolution_width = Column(SmallInteger, check_range('resolution_width', 10, 20000),
                              nullable=True)
    resolution_width.comment = """The maximum horizontal resolution the
    monitor can natively support in pixels.
    """
    resolution_height = Column(SmallInteger, check_range('resolution_height', 10, 20000),
                               nullable=True)
    resolution_height.comment = """The maximum vertical resolution the
    monitor can natively support in pixels.
    """
    refresh_rate = Column(SmallInteger, check_range('refresh_rate', 10, 1000))
    contrast_ratio = Column(SmallInteger, check_range('contrast_ratio', 100, 100000))
    touchable = Column(Boolean)
    touchable.comment = """Whether it is a touchscreen."""

    @hybrid_property
    def aspect_ratio(self):
        """The aspect ratio of the display, as a fraction: ``X/Y``.

        Regular values are ``4/3``, ``5/4``, ``16/9``, ``21/9``,
        ``14/10``, ``19/10``, ``16/10``.
        """
        if self.resolution_height and self.resolution_width:
            return Fraction(self.resolution_width, self.resolution_height)
        return 0

    # noinspection PyUnresolvedReferences
    @aspect_ratio.expression
    def aspect_ratio(cls):
        # The aspect ratio to use as SQL in the DB
        # This allows comparing resolutions
        return db.func.round(cls.resolution_width / cls.resolution_height, 2)

    @hybrid_property
    def widescreen(self):
        """Whether the monitor is considered to be widescreen.

        Widescreen monitors are those having a higher aspect ratio
        greater than 4/3.
        """
        # We add a tiny extra to 4/3 to avoid precision errors
        return self.aspect_ratio > 4.001 / 3

    def __str__(self) -> str:
        if self.size:
            return '{0.t} {0.serial_number} {0.size}in ({0.aspect_ratio}) {0.technology}'.format(self)
        return '{0.t} {0.serial_number} 0in ({0.aspect_ratio}) {0.technology}'.format(self)

    def __format__(self, format_spec: str) -> str:
        v = ''
        if 't' in format_spec:
            v += '{0.t} {0.model}'.format(self)
        if 's' in format_spec:
            v += '({0.manufacturer}) S/N {0.serial_number}'.format(self)
            if self.size:
                v += '– {0.size}in ({0.aspect_ratio}) {0.technology}'.format(self)
            else:
                v += '– 0in ({0.aspect_ratio}) {0.technology}'.format(self)
        return v


class Computer(Device):
    """A chassis with components inside that can be processed
    automatically with Workbench Computer.

    Computer is broadly extended by ``Desktop``, ``Laptop``, and
    ``Server``. The property ``chassis`` defines it more granularly.
    """
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    chassis = Column(DBEnum(ComputerChassis), nullable=True)
    chassis.comment = """The physical form of the computer.

    It is a subset of the Linux definition of DMI / DMI decode.
    """
    ethereum_address = Column(CIText(), unique=True, default=None)
    deposit = Column(Integer, check_range('deposit', min=0, max=100), default=0)
    owner_id = db.Column(UUID(as_uuid=True),
                         db.ForeignKey(User.id),
                         nullable=False,
                         default=lambda: g.user.id)
    author = db.relationship(User, primaryjoin=owner_id == User.id)
    transfer_state = db.Column(IntEnum(TransferState), default=TransferState.Initial, nullable=False)
    transfer_state.comment = TransferState.__doc__
    receiver_id = db.Column(UUID(as_uuid=True),
                            db.ForeignKey(User.id),
                            nullable=True)
    receiver = db.relationship(User, primaryjoin=receiver_id == User.id)
    deliverynote_address = db.Column(CIText(), nullable=True)

    def __init__(self, *args, **kwargs) -> None:
        if args:
            chassis = ComputerChassis(args[0])
            super().__init__(chassis=chassis, **kwargs)
        else:
            super().__init__(*args, **kwargs)

    @property
    def actions(self) -> list:
        return sorted(chain(super().actions, self.actions_parent))

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

    @property
    def privacy(self):
        """Returns the privacy of all ``DataStorage`` components when
        it is not None.
        """
        return set(
            privacy for privacy in
            (hdd.privacy for hdd in self.components if isinstance(hdd, DataStorage))
            if privacy
        )

    def add_mac_to_hid(self, components_snap=None):
        """Returns the Naming.hid with the first mac of network adapter, 
        following an alphabetical order.
        """
        self.set_hid()
        if not self.hid:
            return
        components = self.components if components_snap is None else components_snap
        macs_network = [c.serial_number for c in components
                        if c.type == 'NetworkAdapter' and c.serial_number is not None]
        macs_network.sort()
        mac = macs_network[0] if macs_network else ''
        if not mac or mac in self.hid:
            return
        mac = f"-{mac}"
        self.hid += mac

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
    layout = Column(DBEnum(Layouts))
    layout.comment = """Layout of a built-in keyboard of the computer,
     if any.
     """


class Server(Computer):
    pass


class Monitor(DisplayMixin, Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)


class ComputerMonitor(Monitor):
    pass


class TelevisionSet(Monitor):
    pass


class Projector(Monitor):
    pass


class Mobile(Device):
    """A mobile device consisting of smartphones, tablets, and cellphones."""

    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    imei = Column(BigInteger)
    imei.comment = """The International Mobile Equipment Identity of
    the smartphone as an integer.
    """
    meid = Column(Unicode)
    meid.comment = """The Mobile Equipment Identifier as a hexadecimal
    string.
    """
    ram_size = db.Column(db.Integer, check_range('ram_size', min=128, max=36000))
    ram_size.comment = """The total of RAM of the device in MB."""
    data_storage_size = db.Column(db.Integer, check_range('data_storage_size', 0, 10 ** 8))
    data_storage_size.comment = """The total of data storage of the device in MB"""
    display_size = db.Column(db.Float(decimal_return_scale=1), check_range('display_size', min=0.1, max=30.0))
    display_size.comment = """The total size of the device screen"""

    @validates('imei')
    def validate_imei(self, _, value: int):
        if not imei.is_valid(str(value)):
            raise ValidationError('{} is not a valid imei.'.format(value))
        return value

    @validates('meid')
    def validate_meid(self, _, value: str):
        if not meid.is_valid(value):
            raise ValidationError('{} is not a valid meid.'.format(value))
        return value


class Smartphone(Mobile):
    pass


class Tablet(Mobile):
    pass


class Cellphone(Mobile):
    pass


class Component(Device):
    """A device that can be inside another device."""
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)

    parent_id = Column(BigInteger, ForeignKey(Computer.id))
    parent = relationship(Computer,
                          backref=backref('components',
                                          lazy=True,
                                          cascade=CASCADE_DEL,
                                          order_by=lambda: Component.id,
                                          collection_class=OrderedSet),
                          primaryjoin=parent_id == Computer.id)

    __table_args__ = (
        db.Index('parent_index', parent_id, postgresql_using='hash'),
    )

    def similar_one(self, parent: Computer, blacklist: Set[int]) -> 'Component':
        """Gets a component that:

        * has the same parent.
        * Doesn't generate HID.
        * Has same physical properties.
        :param parent:
        :param blacklist: A set of components to not to consider
                          when looking for similar ones.
        """
        assert self.hid is None, 'Don\'t use this method with a component that has HID'
        component = self.__class__.query \
            .filter_by(parent=parent, hid=None, owner_id=self.owner_id, 
                       **self.physical_properties) \
            .filter(~Component.id.in_(blacklist)) \
            .first()
        if not component:
            raise ResourceNotFound(self.type)
        return component

    @property
    def actions(self) -> list:
        return sorted(chain(super().actions, self.actions_components))


class JoinedComponentTableMixin:
    @declared_attr
    def id(cls):
        return Column(BigInteger, ForeignKey(Component.id), primary_key=True)


class GraphicCard(JoinedComponentTableMixin, Component):
    memory = Column(SmallInteger, check_range('memory', min=1, max=10000))
    memory.comment = """The amount of memory of the Graphic Card in MB."""


class DataStorage(JoinedComponentTableMixin, Component):
    """A device that stores information."""
    size = Column(Integer, check_range('size', min=1, max=10 ** 8))
    size.comment = """The size of the data-storage in MB."""
    interface = Column(DBEnum(DataStorageInterface))

    @property
    def privacy(self):
        """Returns the privacy compliance state of the data storage.

        This is, the last erasure performed to the data storage.
        """
        from ereuse_devicehub.resources.action.models import EraseBasic
        try:
            ev = self.last_action_of(EraseBasic)
        except LookupError:
            ev = None
        return ev

    def __format__(self, format_spec):
        v = super().__format__(format_spec)
        if 's' in format_spec:
            v += ' – {} GB'.format(self.size // 1000 if self.size else '?')
        return v


class HardDrive(DataStorage):
    pass


class SolidStateDrive(DataStorage):
    pass


class Motherboard(JoinedComponentTableMixin, Component):
    slots = Column(SmallInteger, check_range('slots', min=0))
    slots.comment = """PCI slots the motherboard has."""
    usb = Column(SmallInteger, check_range('usb', min=0))
    firewire = Column(SmallInteger, check_range('firewire', min=0))
    serial = Column(SmallInteger, check_range('serial', min=0))
    pcmcia = Column(SmallInteger, check_range('pcmcia', min=0))
    bios_date = Column(db.Date)
    bios_date.comment = """The date of the BIOS version."""
    ram_slots = Column(db.SmallInteger, check_range('ram_slots'))
    ram_max_size = Column(db.Integer, check_range('ram_max_size'))


class NetworkMixin:
    speed = Column(SmallInteger, check_range('speed', min=10, max=10000))
    speed.comment = """The maximum speed this network adapter can handle,
    in mbps.
    """
    wireless = Column(Boolean, nullable=False, default=False)
    wireless.comment = """Whether it is a wireless interface."""

    def __format__(self, format_spec):
        v = super().__format__(format_spec)
        if 's' in format_spec:
            v += ' – {} Mbps'.format(self.speed)
        return v


class NetworkAdapter(JoinedComponentTableMixin, NetworkMixin, Component):
    pass


class Processor(JoinedComponentTableMixin, Component):
    """The CPU."""
    speed = Column(Float, check_range('speed', 0.1, 15))
    speed.comment = """The regular CPU speed."""
    cores = Column(SmallInteger, check_range('cores', 1, 10))
    cores.comment = """The number of regular cores."""
    threads = Column(SmallInteger, check_range('threads', 1, 20))
    threads.comment = """The number of threads per core."""
    address = Column(SmallInteger, check_range('address', 8, 256))
    address.comment = """The address of the CPU: 8, 16, 32, 64, 128 or 256 bits."""
    abi = Column(Unicode, check_lower('abi'))
    abi.comment = """The Application Binary Interface of the processor."""


class RamModule(JoinedComponentTableMixin, Component):
    """A stick of RAM."""
    size = Column(SmallInteger, check_range('size', min=128, max=17000))
    size.comment = """The capacity of the RAM stick."""
    speed = Column(SmallInteger, check_range('speed', min=100, max=10000))
    interface = Column(DBEnum(RamInterface))
    format = Column(DBEnum(RamFormat))


class SoundCard(JoinedComponentTableMixin, Component):
    pass


class Display(JoinedComponentTableMixin, DisplayMixin, Component):
    """The display of a device. This is used in all devices that have
    displays but that it is not their main part, like laptops,
    mobiles, smart-watches, and so on; excluding ``ComputerMonitor``
    and ``TelevisionSet``.
    """
    pass


class Battery(JoinedComponentTableMixin, Component):
    wireless = db.Column(db.Boolean)
    wireless.comment = """If the battery can be charged wirelessly."""
    technology = db.Column(db.Enum(BatteryTechnology))
    size = db.Column(db.Integer, nullable=False)
    size.comment = """Maximum battery capacity by design, in mAh.

    Use BatteryTest's "size" to get the actual size of the battery.
    """

    @property
    def capacity(self) -> float:
        """The quantity of """
        from ereuse_devicehub.resources.action.models import MeasureBattery
        real_size = self.last_action_of(MeasureBattery).size
        return real_size / self.size if real_size and self.size else None


class Camera(Component):
    """The camera of a device."""
    focal_length = db.Column(db.SmallInteger)
    video_height = db.Column(db.SmallInteger)
    video_width = db.Column(db.Integer)
    horizontal_view_angle = db.Column(db.Integer)
    facing = db.Column(db.Enum(CameraFacing))
    vertical_view_angle = db.Column(db.SmallInteger)
    video_stabilization = db.Column(db.Boolean)
    flash = db.Column(db.Boolean)


class ComputerAccessory(Device):
    """Computer peripherals and similar accessories."""
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    pass


class SAI(ComputerAccessory):
    pass


class Keyboard(ComputerAccessory):
    layout = Column(DBEnum(Layouts))  # If we want to do it not null


class Mouse(ComputerAccessory):
    pass


class MemoryCardReader(ComputerAccessory):
    pass


class Networking(NetworkMixin, Device):
    """Routers, switches, hubs..."""
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)


class Router(Networking):
    pass


class Switch(Networking):
    pass


class Hub(Networking):
    pass


class WirelessAccessPoint(Networking):
    pass


class Printer(Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    wireless = Column(Boolean, nullable=False, default=False)
    wireless.comment = """Whether it is a wireless printer."""
    scanning = Column(Boolean, nullable=False, default=False)
    scanning.comment = """Whether the printer has scanning capabilities."""
    technology = Column(DBEnum(PrinterTechnology))
    technology.comment = """Technology used to print."""
    monochrome = Column(Boolean, nullable=False, default=True)
    monochrome.comment = """Whether the printer is only monochrome."""


class LabelPrinter(Printer):
    pass


class Sound(Device):
    pass


class Microphone(Sound):
    pass


class Video(Device):
    """Devices related to video treatment."""
    pass


class VideoScaler(Video):
    pass


class Videoconference(Video):
    pass


class Cooking(Device):
    """Cooking devices."""
    pass


class Mixer(Cooking):
    pass


class DIYAndGardening(Device):
    pass


class Drill(DIYAndGardening):
    max_drill_bit_size = db.Column(db.SmallInteger)


class PackOfScrewdrivers(Device):
    pass


class Home(Device):
    pass


class Dehumidifier(Home):
    size = db.Column(db.SmallInteger)
    size.comment = """The capacity in Liters."""


class Stairs(Home):
    max_allowed_weight = db.Column(db.Integer)


class Recreation(Device):
    pass


class Bike(Recreation):
    wheel_size = db.Column(db.SmallInteger)
    gears = db.Column(db.SmallInteger)


class Racket(Recreation):
    pass


class Manufacturer(db.Model):
    """The normalized information about a manufacturer.

    Ideally users should use the names from this list when submitting
    devices.
    """
    name = db.Column(CIText(), primary_key=True)
    name.comment = """The normalized name of the manufacturer."""
    url = db.Column(URL(), unique=True)
    url.comment = """An URL to a page describing the manufacturer."""
    logo = db.Column(URL())
    logo.comment = """An URL pointing to the logo of the manufacturer."""

    __table_args__ = (
        # from https://niallburkley.com/blog/index-columns-for-like-in-postgres/
        db.Index('name_index', text('name gin_trgm_ops'), postgresql_using='gin'),
        {'schema': 'common'}
    )

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


listener_reset_field_updated_in_actual_time(Device)
