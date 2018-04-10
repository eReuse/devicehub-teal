from sqlalchemy import BigInteger, Column, Float, ForeignKey, Integer, Sequence, SmallInteger, \
    Unicode
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import backref, relationship

from ereuse_devicehub.resources.model import STR_BIG_SIZE, STR_SIZE, Thing, check_range
from teal.db import POLYMORPHIC_ID, POLYMORPHIC_ON, CASCADE


class Device(Thing):
    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)
    type = Column(Unicode)
    pid = Column(Unicode(STR_SIZE), unique=True)
    gid = Column(Unicode(STR_SIZE), unique=True)
    hid = Column(Unicode(STR_BIG_SIZE), unique=True)
    model = Column(Unicode(STR_BIG_SIZE))
    manufacturer = Column(Unicode(STR_SIZE))
    serial_number = Column(Unicode(STR_SIZE))
    weight = Column(Float(precision=3), check_range('weight', min=0.1))
    width = Column(Float(precision=3), check_range('width', min=0.1))
    height = Column(Float(precision=3), check_range('height', min=0.1))

    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.__name__}
        if cls.__name__ == 'Device':
            args[POLYMORPHIC_ON] = cls.type
        return args


class Computer(Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)


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
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)

    parent_id = Column(BigInteger, ForeignKey('computer.id'))
    parent = relationship(Computer,
                          backref=backref('components', lazy=True, cascade=CASCADE),
                          primaryjoin='Component.parent_id == Computer.id')


class GraphicCard(Component):
    memory = Column(SmallInteger, check_range('memory', min=0.1))


class HardDrive(Component):
    size = Column(Integer, check_range('size', min=0.1))


class Motherboard(Component):
    slots = Column(SmallInteger, check_range('slots'))
    usb = Column(SmallInteger, check_range('usb'))
    firewire = Column(SmallInteger, check_range('firewire'))
    serial = Column(SmallInteger, check_range('serial'))
    pcmcia = Column(SmallInteger, check_range('pcmcia'))


class NetworkAdapter(Component):
    speed = Column(SmallInteger, check_range('speed'))
