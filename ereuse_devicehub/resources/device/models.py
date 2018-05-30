from contextlib import suppress
from itertools import chain
from operator import attrgetter
from typing import Dict, Set

from ereuse_utils.naming import Naming
from sqlalchemy import BigInteger, Column, Float, ForeignKey, Integer, Sequence, SmallInteger, \
    Unicode, inspect
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import ColumnProperty, backref, relationship
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE, STR_SM_SIZE, Thing
from teal.db import CASCADE, POLYMORPHIC_ID, POLYMORPHIC_ON, ResourceNotFound, check_range


class Device(Thing):
    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)  # type: int
    type = Column(Unicode(STR_SM_SIZE), nullable=False)
    hid = Column(Unicode(STR_BIG_SIZE), unique=True)  # type: str
    pid = Column(Unicode(STR_SIZE))  # type: str
    gid = Column(Unicode(STR_SIZE))  # type: str
    model = Column(Unicode(STR_BIG_SIZE))  # type: str
    manufacturer = Column(Unicode(STR_SIZE))  # type: str
    serial_number = Column(Unicode(STR_SIZE))  # type: str
    weight = Column(Float(precision=3, decimal_return_scale=3),
                    check_range('weight', 0.1, 3))  # type: float
    width = Column(Float(precision=3, decimal_return_scale=3),
                   check_range('width', 0.1, 3))  # type: float
    height = Column(Float(precision=3, decimal_return_scale=3),
                    check_range('height', 0.1, 3))  # type: float

    @property
    def events(self) -> list:
        """All the events performed to the device."""
        return sorted(chain(self.events_multiple, self.events_one), key=attrgetter('id'))

    def __init__(self, *args, **kw) -> None:
        super().__init__(*args, **kw)
        with suppress(TypeError):
            self.hid = Naming.hid(self.manufacturer, self.serial_number, self.model)  # type: str

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


class Computer(Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)  # type: int


class Desktop(Computer):
    pass


class Laptop(Computer):
    pass


class Netbook(Computer):
    pass


class Server(Computer):
    pass


class Microtower(Computer):
    pass


class Component(Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)  # type: int

    parent_id = Column(BigInteger, ForeignKey(Computer.id))
    parent = relationship(Computer,
                          backref=backref('components',
                                          lazy=True,
                                          cascade=CASCADE,
                                          order_by=lambda: Component.id,
                                          collection_class=OrderedSet),
                          primaryjoin=parent_id == Computer.id)  # type: Device

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
        return sorted(chain(super().events, self.events_components), key=attrgetter('id'))


class JoinedComponentTableMixin:
    @declared_attr
    def id(cls):
        return Column(BigInteger, ForeignKey(Component.id), primary_key=True)


class GraphicCard(JoinedComponentTableMixin, Component):
    memory = Column(SmallInteger, check_range('memory', min=1, max=10000))  # type: int


class HardDrive(JoinedComponentTableMixin, Component):
    size = Column(Integer, check_range('size', min=1, max=10 ** 8))  # type: int


class Motherboard(JoinedComponentTableMixin, Component):
    slots = Column(SmallInteger, check_range('slots'))  # type: int
    usb = Column(SmallInteger, check_range('usb'))  # type: int
    firewire = Column(SmallInteger, check_range('firewire'))  # type: int
    serial = Column(SmallInteger, check_range('serial'))  # type: int
    pcmcia = Column(SmallInteger, check_range('pcmcia'))  # type: int


class NetworkAdapter(JoinedComponentTableMixin, Component):
    speed = Column(SmallInteger, check_range('speed', min=10, max=10000))  # type: int


class Processor(JoinedComponentTableMixin, Component):
    speed = Column(Float, check_range('speed', 0.1, 15))
    cores = Column(SmallInteger, check_range('cores', 1, 10))
    address = Column(SmallInteger, check_range('address', 8, 256))


class RamModule(JoinedComponentTableMixin, Component):
    size = Column(SmallInteger, check_range('size', min=128, max=17000))
    speed = Column(Float, check_range('speed', min=100, max=10000))
