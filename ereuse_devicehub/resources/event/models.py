from uuid import uuid4

from flask import g
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, Enum as DBEnum, \
    Float, ForeignKey, Interval, JSON, SmallInteger, Unicode, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import backref, relationship
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Component, DataStorage, Device
from ereuse_devicehub.resources.enums import AppearanceRange, BOX_RATE_3, BOX_RATE_5, Bios, \
    FunctionalityRange, RATE_NEGATIVE, RATE_POSITIVE, RatingRange, RatingSoftware, \
    SnapshotExpectedEvents, SnapshotSoftware, TestHardDriveLength
from ereuse_devicehub.resources.image.models import Image
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE, STR_SM_SIZE, Thing
from ereuse_devicehub.resources.user.models import User
from teal.db import ArrayOfEnum, CASCADE, CASCADE_OWN, INHERIT_COND, POLYMORPHIC_ID, \
    POLYMORPHIC_ON, StrictVersionType, check_range


class JoinedTableMixin:
    # noinspection PyMethodParameters
    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), ForeignKey(Event.id), primary_key=True)


class Event(Thing):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(Unicode(STR_BIG_SIZE), default='', nullable=False)
    type = Column(Unicode)
    incidence = Column(Boolean, default=False, nullable=False)
    closed = Column(Boolean, default=True, nullable=False)
    """
    Whether the author has finished the event.
    After this is set to True, no modifications are allowed.
    """
    error = Column(Boolean, default=False, nullable=False)
    description = Column(Unicode, default='', nullable=False)
    date = Column(DateTime)

    snapshot_id = Column(UUID(as_uuid=True), ForeignKey('snapshot.id',
                                                        use_alter=True,
                                                        name='snapshot_events'))
    snapshot = relationship('Snapshot',
                            backref=backref('events',
                                            lazy=True,
                                            cascade=CASCADE_OWN,
                                            collection_class=set),
                            primaryjoin='Event.snapshot_id == Snapshot.id')

    author_id = Column(UUID(as_uuid=True),
                       ForeignKey(User.id),
                       nullable=False,
                       default=lambda: g.user.id)
    author = relationship(User,
                          backref=backref('events', lazy=True, collection_class=set),
                          primaryjoin=author_id == User.id)
    components = relationship(Component,
                              backref=backref('events_components',
                                              lazy=True,
                                              order_by=lambda: Event.created,
                                              collection_class=OrderedSet),
                              secondary=lambda: EventComponent.__table__,
                              order_by=lambda: Component.id,
                              collection_class=OrderedSet)
    """
    The components that are affected by the event.
    
    When performing events to parent devices their components are
    affected too.
    
    For example: an ``Allocate`` is performed to a Computer and this
    relationship is filled with the components the computer had
    at the time of the event.
    """

    # noinspection PyMethodParameters
    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Event':
            args[POLYMORPHIC_ON] = cls.type
        if JoinedTableMixin in cls.mro():
            args[INHERIT_COND] = cls.id == Event.id
        return args


class EventComponent(db.Model):
    device_id = Column(BigInteger, ForeignKey(Component.id), primary_key=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey(Event.id), primary_key=True)


class EventWithOneDevice(Event):
    device_id = Column(BigInteger, ForeignKey(Device.id), nullable=False)
    device = relationship(Device,
                          backref=backref('events_one',
                                          lazy=True,
                                          cascade=CASCADE,
                                          order_by=lambda: EventWithOneDevice.created,
                                          collection_class=OrderedSet),
                          primaryjoin=Device.id == device_id)

    def __repr__(self) -> str:
        return '<{0.t} {0.id!r} device={0.device_id}>'.format(self)


class EventWithMultipleDevices(Event):
    devices = relationship(Device,
                           backref=backref('events_multiple',
                                           lazy=True,
                                           order_by=lambda: EventWithMultipleDevices.created,
                                           collection_class=OrderedSet),
                           secondary=lambda: EventDevice.__table__,
                           order_by=lambda: Device.id)

    def __repr__(self) -> str:
        return '<{0.t} {0.id!r} devices={0.devices!r}>'.format(self)


class EventDevice(db.Model):
    device_id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey(EventWithMultipleDevices.id),
                      primary_key=True)


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
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, CheckConstraint('end_time > start_time'), nullable=False)
    secure_random_steps = Column(SmallInteger,
                                 check_range('secure_random_steps', min=0),
                                 nullable=False)
    clean_with_zeros = Column(Boolean, nullable=False)


class EraseSectors(EraseBasic):
    pass


class Step(db.Model):
    erasure_id = Column(UUID(as_uuid=True), ForeignKey(EraseBasic.id), primary_key=True)
    type = Column(Unicode(STR_SM_SIZE), nullable=False)
    num = Column(SmallInteger, primary_key=True)
    error = Column(Boolean, default=False, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, CheckConstraint('end_time > start_time'), nullable=False)
    secure_random_steps = Column(SmallInteger,
                                 check_range('secure_random_steps', min=0),
                                 nullable=False)
    clean_with_zeros = Column(Boolean, nullable=False)

    erasure = relationship(EraseBasic,
                           backref=backref('steps',
                                           cascade=CASCADE_OWN,
                                           order_by=num,
                                           collection_class=ordering_list('num')))

    # noinspection PyMethodParameters
    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Step':
            args[POLYMORPHIC_ON] = cls.type
        return args


class StepZero(Step):
    pass


class StepRandom(Step):
    pass


class Snapshot(JoinedTableMixin, EventWithOneDevice):
    uuid = Column(UUID(as_uuid=True), nullable=False, unique=True)
    version = Column(StrictVersionType(STR_SM_SIZE), nullable=False)
    software = Column(DBEnum(SnapshotSoftware), nullable=False)
    elapsed = Column(Interval, nullable=False)
    expected_events = Column(ArrayOfEnum(DBEnum(SnapshotExpectedEvents)))


class Install(JoinedTableMixin, EventWithOneDevice):
    name = Column(Unicode(STR_BIG_SIZE), nullable=False)
    elapsed = Column(Interval, nullable=False)


class SnapshotRequest(db.Model):
    id = Column(UUID(as_uuid=True), ForeignKey(Snapshot.id), primary_key=True)
    request = Column(JSON, nullable=False)
    snapshot = relationship(Snapshot,
                            backref=backref('request',
                                            lazy=True,
                                            uselist=False,
                                            cascade=CASCADE_OWN))


class Rate(JoinedTableMixin, EventWithOneDevice):
    rating = Column(Float(decimal_return_scale=2), check_range('rating', *RATE_POSITIVE))
    algorithm_software = Column(DBEnum(RatingSoftware), nullable=False)
    algorithm_version = Column(StrictVersionType, nullable=False)
    appearance = Column(Float(decimal_return_scale=2), check_range('appearance', *RATE_NEGATIVE))
    functionality = Column(Float(decimal_return_scale=2),
                           check_range('functionality', *RATE_NEGATIVE))

    @property
    def rating_range(self) -> RatingRange:
        return RatingRange.from_score(self.rating)


class IndividualRate(Rate):
    pass


class AggregateRate(Rate):
    id = Column(UUID(as_uuid=True), ForeignKey(Rate.id), primary_key=True)
    ratings = relationship(IndividualRate,
                           backref=backref('aggregated_ratings',
                                           lazy=True,
                                           order_by=lambda: IndividualRate.created,
                                           collection_class=OrderedSet),
                           secondary=lambda: RateAggregateRate.__table__,
                           order_by=lambda: IndividualRate.created,
                           collection_class=OrderedSet)
    """The ratings this aggregateRate aggregates."""


class RateAggregateRate(db.Model):
    """
    Represents the ``many to many`` relationship between
    ``Rate`` and ``AggregateRate``.
    """
    rate_id = Column(UUID(as_uuid=True), ForeignKey(Rate.id), primary_key=True)
    aggregate_rate_id = Column(UUID(as_uuid=True),
                               ForeignKey(AggregateRate.id),
                               primary_key=True)


class WorkbenchRate(IndividualRate):
    id = Column(UUID(as_uuid=True), ForeignKey(Rate.id), primary_key=True)
    processor = Column(Float(decimal_return_scale=2), check_range('processor', *RATE_POSITIVE))
    ram = Column(Float(decimal_return_scale=2), check_range('ram', *RATE_POSITIVE))
    data_storage = Column(Float(decimal_return_scale=2),
                          check_range('data_storage', *RATE_POSITIVE))
    graphic_card = Column(Float(decimal_return_scale=2),
                          check_range('graphic_card', *RATE_POSITIVE))
    labelling = Column(Boolean)
    bios = Column(DBEnum(Bios))
    appearance_range = Column(DBEnum(AppearanceRange))
    functionality_range = Column(DBEnum(FunctionalityRange))


class PhotoboxRate(IndividualRate):
    id = Column(UUID(as_uuid=True), ForeignKey(Rate.id), primary_key=True)
    image_id = Column(UUID(as_uuid=True), ForeignKey(Image.id), nullable=False)
    image = relationship(Image,
                         uselist=False,
                         cascade=CASCADE_OWN,
                         single_parent=True,
                         primaryjoin=Image.id == image_id)

    # todo how to ensure phtoboxrate.device == image.image_list.device?


class PhotoboxUserRate(PhotoboxRate):
    id = Column(UUID(as_uuid=True), ForeignKey(PhotoboxRate.id), primary_key=True)
    assembling = Column(SmallInteger, check_range('assembling', *BOX_RATE_5), nullable=False)
    parts = Column(SmallInteger, check_range('parts', *BOX_RATE_5), nullable=False)
    buttons = Column(SmallInteger, check_range('buttons', *BOX_RATE_5), nullable=False)
    dents = Column(SmallInteger, check_range('dents', *BOX_RATE_5), nullable=False)
    decolorization = Column(SmallInteger,
                            check_range('decolorization', *BOX_RATE_5),
                            nullable=False)
    scratches = Column(SmallInteger, check_range('scratches', *BOX_RATE_5), nullable=False)
    tag_alignment = Column(SmallInteger,
                           check_range('tag_alignment', *BOX_RATE_3),
                           nullable=False)
    tag_adhesive = Column(SmallInteger, check_range('tag_adhesive', *BOX_RATE_3), nullable=False)
    dirt = Column(SmallInteger, check_range('dirt', *BOX_RATE_3), nullable=False)


class PhotoboxSystemRate(PhotoboxRate):
    id = Column(UUID(as_uuid=True), ForeignKey(PhotoboxRate.id), primary_key=True)


class Test(JoinedTableMixin, EventWithOneDevice):
    elapsed = Column(Interval, nullable=False)


class TestDataStorage(Test):
    id = Column(UUID(as_uuid=True), ForeignKey(Test.id), primary_key=True)
    length = Column(DBEnum(TestHardDriveLength), nullable=False)  # todo from type
    status = Column(Unicode(STR_SIZE), nullable=False)
    lifetime = Column(Interval, nullable=False)
    first_error = Column(SmallInteger, nullable=False, default=0)
    passed_lifetime = Column(Interval)
    assessment = Column(Boolean)
    reallocated_sector_count = Column(SmallInteger)
    power_cycle_count = Column(SmallInteger)
    reported_uncorrectable_errors = Column(SmallInteger)
    command_timeout = Column(SmallInteger)
    current_pending_sector_count = Column(SmallInteger)
    offline_uncorrectable = Column(SmallInteger)
    remaining_lifetime_percentage = Column(SmallInteger)

    # todo remove lifetime / passed_lifetime as I think they are the same


class StressTest(Test):
    pass


# Listeners
@event.listens_for(TestDataStorage.device, 'set', retval=True, propagate=True)
@event.listens_for(Install.device, 'set', retval=True, propagate=True)
@event.listens_for(EraseBasic.device, 'set', retval=True, propagate=True)
def validate_device_is_data_storage(target, value, old_value, initiator):
    if not isinstance(value, DataStorage):
        raise TypeError('{} must be a DataStorage but you passed {}'.format(initiator.impl, value))
    return value

# todo finish adding events
# @event.listens_for(Install.snapshot, 'before_insert', propagate=True)
# def validate_required_snapshot(mapper, connection, target: Event):
#    if not target.snapshot:
#        raise ValidationError('{0!r} must be linked to a Snapshot.'.format(target))
