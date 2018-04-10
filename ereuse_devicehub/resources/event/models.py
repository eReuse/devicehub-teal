from enum import Enum

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, Enum as DBEnum, \
    ForeignKey, Integer, Interval, JSON, Sequence, SmallInteger, Unicode
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import backref, relationship

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.model import STR_SIZE, Thing, check_range
from ereuse_devicehub.resources.user.model import User
from teal.db import CASCADE, CASCADE_OWN, INHERIT_COND, POLYMORPHIC_ID, POLYMORPHIC_ON


class JoinedTableMixin:
    @declared_attr
    def id(cls):
        return Column(BigInteger, ForeignKey(Event.id), primary_key=True)


class Event(Thing):
    id = Column(BigInteger, Sequence('event_seq'), primary_key=True)
    date = Column(DateTime)
    secured = Column(Boolean, default=False, nullable=False)
    type = Column(Unicode)
    incidence = Column(Boolean, default=False, nullable=False)

    snapshot_id = Column(BigInteger, ForeignKey('snapshot.id',
                                                use_alter=True,
                                                name='snapshot_events'))
    snapshot = relationship('Snapshot',
                            backref=backref('events', lazy=True, cascade=CASCADE),
                            primaryjoin='Event.snapshot_id == Snapshot.id')

    author_id = Column(BigInteger, ForeignKey(User.id), nullable=False)
    author = relationship(User,
                          backref=backref('events', lazy=True),
                          primaryjoin=author_id == User.id)

    components = relationship(Device,
                              backref=backref('events_components', lazy=True),
                              secondary=lambda: EventComponent.__table__)

    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.__name__}
        if cls.__name__ == 'Event':
            args[POLYMORPHIC_ON] = cls.type
        if JoinedTableMixin in cls.mro():
            args[INHERIT_COND] = cls.id == Event.id
        return args


class EventComponent(db.Model):
    device_id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    event_id = Column(BigInteger, ForeignKey(Event.id), primary_key=True)


class EventWithOneDevice(Event):
    device_id = Column(BigInteger, ForeignKey(Device.id), nullable=False)
    device = relationship(Device,
                          backref=backref('events_one', lazy=True, cascade=CASCADE),
                          primaryjoin=Device.id == device_id)


class EventWithMultipleDevices(Event):
    """
    Note that these events are not deleted when a device is deleted.
    """
    devices = relationship(Device,
                           backref=backref('events', lazy=True),
                           secondary=lambda: EventDevice.__table__)


class EventDevice(db.Model):
    device_id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    event_id = Column(BigInteger, ForeignKey(EventWithMultipleDevices.id), primary_key=True)


class Add(EventWithOneDevice):
    pass


class Remove(EventWithOneDevice):
    pass


class Allocate(JoinedTableMixin, EventWithMultipleDevices):
    to_id = Column(BigInteger, ForeignKey(User.id))
    to = relationship(User, primaryjoin=User.id == to_id)


class Deallocate(JoinedTableMixin, EventWithMultipleDevices):
    from_id = Column(BigInteger, ForeignKey(User.id))
    from_rel = relationship(User, primaryjoin=User.id == from_id)


class EraseBasic(JoinedTableMixin, EventWithOneDevice):
    starting_time = Column(DateTime, nullable=False)
    ending_time = Column(DateTime, nullable=False)
    secure_random_steps = Column(SmallInteger, check_range('secure_random_steps', min=0),
                                 nullable=False)
    success = Column(Boolean, nullable=False)
    clean_with_zeros = Column(Boolean, nullable=False)


class EraseSectors(EraseBasic):
    pass


class StepTypes(Enum):
    Zeros = 1
    Random = 2


class Step(db.Model):
    id = Column(BigInteger, Sequence('step_seq'), primary_key=True)
    num = Column(SmallInteger, primary_key=True)
    type = Column(DBEnum(StepTypes), nullable=False)
    success = Column(Boolean, nullable=False)
    starting_time = Column(DateTime, nullable=False)
    ending_time = Column(DateTime, CheckConstraint('ending_time > starting_time'), nullable=False)
    secure_random_steps = Column(SmallInteger, check_range('secure_random_steps', min=0),
                                 nullable=False)
    clean_with_zeros = Column(Boolean, nullable=False)

    erasure_id = Column(BigInteger, ForeignKey(EraseBasic.id))
    erasure = relationship(EraseBasic, backref=backref('steps', cascade=CASCADE_OWN))


class SoftwareType(Enum):
    Workbench = 'Workbench'
    AndroidApp = 'AndroidApp'
    Web = 'Web'
    DesktopApp = 'DesktopApp'


class Appearance(Enum):
    """Grades the imperfections that aesthetically affect the device, but not its usage."""
    Z = '0. The device is new.'
    A = 'A. Is like new (without visual damage)'
    B = 'B. Is in really good condition (small visual damage in difficult places to spot)'
    C = 'C. Is in good condition (small visual damage in parts that are easy to spot, not screens)'
    D = 'D. Is acceptable (visual damage in visible parts, not ¬screens)'
    E = 'E. Is unacceptable (considerable visual damage that can affect usage)'


class Functionality(Enum):
    A = 'A. Everything works perfectly (buttons, and in case of screens there are no scratches)'
    B = 'B. There is a button difficult to press or a small scratch in an edge of a screen'
    C = 'C. A non-important button (or similar) doesn\'t work; screen has multiple scratches in edges'
    D = 'D. Multiple buttons don\'t work; screen has visual damage resulting in uncomfortable usage'


class Bios(Enum):
    A = 'A. If by pressing a key you could access a boot menu with the network boot'
    B = 'B. You had to get into the BIOS, and in less than 5 steps you could set the network boot'
    C = 'C. Like B, but with more than 5 steps'
    D = 'D. Like B or C, but you had to unlock the BIOS (i.e. by removing the battery)'
    E = 'E. The device could not be booted through the network.'


class Snapshot(JoinedTableMixin, EventWithOneDevice):
    uuid = Column(UUID(as_uuid=True), nullable=False, unique=True)
    version = Column(Unicode, nullable=False)
    snapshot_software = Column(DBEnum(SoftwareType), nullable=False)
    appearance = Column(DBEnum(Appearance), nullable=False)
    appearance_score = Column(SmallInteger, nullable=False)
    functionality = Column(DBEnum(Functionality), nullable=False)
    functionality_score = Column(SmallInteger, check_range('functionality_score', min=0, max=5),
                                 nullable=False)
    labelling = Column(Boolean, nullable=False)
    bios = Column(DBEnum(Bios), nullable=False)
    condition = Column(SmallInteger, check_range('condition', min=0, max=5), nullable=False)
    elapsed = Column(Interval, nullable=False)
    install_name = Column(Unicode)
    install_elapsed = Column(Interval)
    install_success = Column(Boolean)
    inventory_elapsed = Column(Interval)


class SnapshotRequest(db.Model):
    id = Column(BigInteger, ForeignKey(Snapshot.id), primary_key=True)
    request = Column(JSON, nullable=False)

    snapshot = relationship(Snapshot, backref=backref('request', lazy=True, uselist=False,
                                                      cascade=CASCADE_OWN))


class Test(JoinedTableMixin, EventWithOneDevice):
    elapsed = Column(Interval, nullable=False)
    success = Column(Boolean, nullable=False)

    snapshot = relationship(Snapshot, backref=backref('tests', lazy=True, cascade=CASCADE_OWN))


class TestHardDriveLength(Enum):
    Short = 'Short'
    Extended = 'Extended'


class TestHardDrive(Test):
    length = Column(DBEnum(TestHardDriveLength), nullable=False)  # todo from type
    status = Column(Unicode(STR_SIZE), nullable=False)
    lifetime = Column(Interval, nullable=False)
    first_error = Column(Integer)
    # todo error becomes Test.success


class StressTest(Test):
    pass
