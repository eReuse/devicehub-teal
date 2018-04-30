from datetime import timedelta

from colour import Color
from flask import g
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, Enum as DBEnum, \
    ForeignKey, Integer, Interval, JSON, Sequence, SmallInteger, Unicode
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy_utils import ColorType

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.event.enums import Appearance, Bios, Functionality, Orientation, \
    SoftwareType, StepTypes, TestHardDriveLength
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE, STR_SM_SIZE, Thing, \
    check_range
from ereuse_devicehub.resources.user.models import User
from teal.db import CASCADE, CASCADE_OWN, INHERIT_COND, POLYMORPHIC_ID, POLYMORPHIC_ON, \
    StrictVersionType


class JoinedTableMixin:
    @declared_attr
    def id(cls):
        return Column(BigInteger, ForeignKey(Event.id), primary_key=True)


class Event(Thing):
    id = Column(BigInteger, Sequence('event_seq'), primary_key=True)
    title = Column(Unicode(STR_BIG_SIZE), default='', nullable=False)
    date = Column(DateTime)
    secured = Column(Boolean, default=False, nullable=False)
    type = Column(Unicode)
    incidence = Column(Boolean, default=False, nullable=False)
    description = Column(Unicode, default='', nullable=False)

    snapshot_id = Column(BigInteger, ForeignKey('snapshot.id',
                                                use_alter=True,
                                                name='snapshot_events'))
    snapshot = relationship('Snapshot',
                            backref=backref('events', lazy=True, cascade=CASCADE),
                            primaryjoin='Event.snapshot_id == Snapshot.id')

    author_id = Column(UUID(as_uuid=True),
                       ForeignKey(User.id),
                       nullable=False,
                       default=lambda: g.user.id)
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
    to_id = Column(UUID, ForeignKey(User.id))
    to = relationship(User, primaryjoin=User.id == to_id)
    organization = Column(Unicode(STR_SIZE))


class Deallocate(JoinedTableMixin, EventWithMultipleDevices):
    from_id = Column(UUID, ForeignKey(User.id))
    from_rel = relationship(User, primaryjoin=User.id == from_id)
    organization = Column(Unicode(STR_SIZE))


class EraseBasic(JoinedTableMixin, EventWithOneDevice):
    starting_time = Column(DateTime, nullable=False)
    ending_time = Column(DateTime, nullable=False)
    secure_random_steps = Column(SmallInteger, check_range('secure_random_steps', min=0),
                                 nullable=False)
    success = Column(Boolean, nullable=False)
    clean_with_zeros = Column(Boolean, nullable=False)


class EraseSectors(EraseBasic):
    pass


class Step(db.Model):
    id = Column(BigInteger, Sequence('step_seq'), primary_key=True)
    num = Column(SmallInteger, nullable=False)
    type = Column(DBEnum(StepTypes), nullable=False)
    success = Column(Boolean, nullable=False)
    starting_time = Column(DateTime, nullable=False)
    ending_time = Column(DateTime, CheckConstraint('ending_time > starting_time'), nullable=False)
    secure_random_steps = Column(SmallInteger, check_range('secure_random_steps', min=0),
                                 nullable=False)
    clean_with_zeros = Column(Boolean, nullable=False)

    erasure_id = Column(BigInteger, ForeignKey(EraseBasic.id))
    erasure = relationship(EraseBasic, backref=backref('steps', cascade=CASCADE_OWN))


class Snapshot(JoinedTableMixin, EventWithOneDevice):
    uuid = Column(UUID(as_uuid=True), nullable=False, unique=True)  # type: UUID
    version = Column(StrictVersionType(STR_SM_SIZE), nullable=False)  # type: str
    software = Column(DBEnum(SoftwareType), nullable=False)  # type: SoftwareType
    appearance = Column(DBEnum(Appearance))  # type: Appearance
    appearance_score = Column(SmallInteger,
                              check_range('appearance_score', -3, 5))  # type: int
    functionality = Column(DBEnum(Functionality))  # type: Functionality
    functionality_score = Column(SmallInteger,
                                 check_range('functionality_score', min=-3, max=5))  # type: int
    labelling = Column(Boolean)  # type: bool
    bios = Column(DBEnum(Bios))  # type: Bios
    condition = Column(SmallInteger,
                       check_range('condition', min=0, max=5))  # type: int
    elapsed = Column(Interval, nullable=False)  # type: timedelta
    install_name = Column(Unicode(STR_BIG_SIZE))  # type: str
    install_elapsed = Column(Interval)  # type: timedelta
    install_success = Column(Boolean)  # type: bool
    inventory_elapsed = Column(Interval)  # type: timedelta
    color = Column(ColorType)  # type: Color
    orientation = Column(DBEnum(Orientation))  # type: Orientation
    force_creation = Column(Boolean)

    @validates('components')
    def validate_components_only_workbench(self, _, components):
        if self.software != SoftwareType.Workbench:
            if components:
                raise ValueError('Only Snapshots from Workbench can have components.')
        return components


class SnapshotRequest(db.Model):
    id = Column(BigInteger, ForeignKey(Snapshot.id), primary_key=True)
    request = Column(JSON, nullable=False)

    snapshot = relationship(Snapshot, backref=backref('request', lazy=True, uselist=False,
                                                      cascade=CASCADE_OWN))


class Test(JoinedTableMixin, EventWithOneDevice):
    elapsed = Column(Interval, nullable=False)
    success = Column(Boolean, nullable=False)

    snapshot = relationship(Snapshot, backref=backref('tests', lazy=True, cascade=CASCADE_OWN))


class TestHardDrive(Test):
    length = Column(DBEnum(TestHardDriveLength), nullable=False)  # todo from type
    status = Column(Unicode(STR_SIZE), nullable=False)
    lifetime = Column(Interval, nullable=False)
    first_error = Column(Integer)
    # todo error becomes Test.success


class StressTest(Test):
    pass
