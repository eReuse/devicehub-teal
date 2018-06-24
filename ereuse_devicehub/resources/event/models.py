from collections import Iterable
from typing import Set, Union
from uuid import uuid4

from flask import g
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, Enum as DBEnum, \
    Float, ForeignKey, Interval, JSON, SmallInteger, Unicode, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import backref, relationship
from sqlalchemy.orm.events import AttributeEvents as Events
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Component, Computer, DataStorage, Device
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
    name = Column(Unicode(STR_BIG_SIZE), default='', nullable=False)
    name.comment = """
        A name or title for the event. Used when searching for events.
    """
    type = Column(Unicode)
    incidence = Column(Boolean, default=False, nullable=False)
    incidence.comment = """
        Should this event be reviewed due some anomaly?
    """
    closed = Column(Boolean, default=True, nullable=False)
    closed.comment = """
        Whether the author has finished the event.
        After this is set to True, no modifications are allowed.
        By default events are closed when performed.
    """
    error = Column(Boolean, default=False, nullable=False)
    error.comment = """
        Did the event fail?
        For example, a failure in ``Erase`` means that the data storage
        unit did not erase correctly.
    """
    description = Column(Unicode, default='', nullable=False)
    description.comment = """
        A comment about the event.
    """
    date = Column(DateTime)
    date.comment = """
        When this event happened.
        Leave it blank if it is happening now
        (the field ``created`` is used instead).
        This is used for example when creating events retroactively.
    """
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
    
    For Add and Remove though, this has another meaning: the components
    that are added or removed.
    """
    parent_id = Column(BigInteger, ForeignKey(Computer.id))
    parent = relationship(Computer,
                          backref=backref('events_parent',
                                          lazy=True,
                                          order_by=lambda: Event.created,
                                          collection_class=OrderedSet),
                          primaryjoin=parent_id == Computer.id)
    """
    For events that are performed to components, the device parent
    at that time.
    
    For example: for a ``EraseBasic`` performed on a data storage, this
    would point to the computer that contained this data storage, if any.
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
        return '<{0.t} {0.id!r} device={0.device!r}>'.format(self)


class EventWithMultipleDevices(Event):
    devices = relationship(Device,
                           backref=backref('events_multiple',
                                           lazy=True,
                                           order_by=lambda: EventWithMultipleDevices.created,
                                           collection_class=OrderedSet),
                           secondary=lambda: EventDevice.__table__,
                           order_by=lambda: Device.id,
                           collection_class=OrderedSet)

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


class Ready(EventWithMultipleDevices):
    pass


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
    uuid = Column(UUID(as_uuid=True), unique=True)
    version = Column(StrictVersionType(STR_SM_SIZE), nullable=False)
    software = Column(DBEnum(SnapshotSoftware), nullable=False)
    elapsed = Column(Interval)
    elapsed.comment = """
        For Snapshots made with Workbench, the total amount of time
        it took to complete.
    """
    expected_events = Column(ArrayOfEnum(DBEnum(SnapshotExpectedEvents)))


class Install(JoinedTableMixin, EventWithOneDevice):
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

    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Rate':
            args[POLYMORPHIC_ON] = cls.type
        return args


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


class ManualRate(IndividualRate):
    id = Column(UUID(as_uuid=True), ForeignKey(Rate.id), primary_key=True)
    labelling = Column(Boolean)
    appearance_range = Column(DBEnum(AppearanceRange))
    functionality_range = Column(DBEnum(FunctionalityRange))


class WorkbenchRate(ManualRate):
    id = Column(UUID(as_uuid=True), ForeignKey(ManualRate.id), primary_key=True)
    processor = Column(Float(decimal_return_scale=2), check_range('processor', *RATE_POSITIVE))
    ram = Column(Float(decimal_return_scale=2), check_range('ram', *RATE_POSITIVE))
    data_storage = Column(Float(decimal_return_scale=2),
                          check_range('data_storage', *RATE_POSITIVE))
    graphic_card = Column(Float(decimal_return_scale=2),
                          check_range('graphic_card', *RATE_POSITIVE))
    bios = Column(DBEnum(Bios))


class AppRate(ManualRate):
    pass


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

    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Test':
            args[POLYMORPHIC_ON] = cls.type
        return args


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


class Benchmark(JoinedTableMixin, EventWithOneDevice):
    elapsed = Column(Interval)

    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Benchmark':
            args[POLYMORPHIC_ON] = cls.type
        return args


class BenchmarkDataStorage(Benchmark):
    id = Column(UUID(as_uuid=True), ForeignKey(Benchmark.id), primary_key=True)
    read_speed = Column(Float(decimal_return_scale=2), nullable=False)
    write_speed = Column(Float(decimal_return_scale=2), nullable=False)


class BenchmarkWithRate(Benchmark):
    id = Column(UUID(as_uuid=True), ForeignKey(Benchmark.id), primary_key=True)
    rate = Column(SmallInteger, nullable=False)


class BenchmarkProcessor(BenchmarkWithRate):
    pass


class BenchmarkProcessorSysbench(BenchmarkProcessor):
    pass


class BenchmarkRamSysbench(BenchmarkWithRate):
    pass


# Listeners
# Listeners validate values and keep relationships synced

@event.listens_for(TestDataStorage.device, Events.set.__name__, propagate=True)
@event.listens_for(Install.device, Events.set.__name__, propagate=True)
@event.listens_for(EraseBasic.device, Events.set.__name__, propagate=True)
def validate_device_is_data_storage(target: Event, value: DataStorage, old_value, initiator):
    """Validates that the device for data-storage events is effectively a data storage."""
    if value and not isinstance(value, DataStorage):
        raise TypeError('{} must be a DataStorage but you passed {}'.format(initiator.impl, value))


# The following listeners keep relationships with device <-> components synced with the event
# So, if you add or remove devices from events these listeners will
# automatically add/remove the ``components`` and ``parent`` of such events
# See the tests for examples

@event.listens_for(EventWithOneDevice.device, Events.set.__name__, propagate=True)
def update_components_event_one(target: EventWithOneDevice, device: Device, __, ___):
    """
    Syncs the :attr:`.Event.components` with the components in
    :attr:`ereuse_devicehub.resources.device.models.Computer.components`.
    """
    # For Add and Remove, ``components`` have different meanings
    # see Event.components for more info
    if not isinstance(target, (Add, Remove)):
        target.components.clear()
        if isinstance(device, Computer):
            target.components |= device.components


@event.listens_for(EventWithMultipleDevices.devices, Events.init_collection.__name__,
                   propagate=True)
@event.listens_for(EventWithMultipleDevices.devices, Events.bulk_replace.__name__, propagate=True)
@event.listens_for(EventWithMultipleDevices.devices, Events.append.__name__, propagate=True)
def update_components_event_multiple(target: EventWithMultipleDevices,
                                     value: Union[Set[Device], Device], _):
    """
    Syncs the :attr:`.Event.components` with the components in
    :attr:`ereuse_devicehub.resources.device.models.Computer.components`.
    """
    target.components.clear()
    devices = value if isinstance(value, Iterable) else {value}
    for device in devices:
        if isinstance(device, Computer):
            target.components |= device.components


@event.listens_for(EventWithMultipleDevices.devices, Events.remove.__name__, propagate=True)
def remove_components_event_multiple(target: EventWithMultipleDevices, device: Device, __):
    """
    Syncs the :attr:`.Event.components` with the components in
    :attr:`ereuse_devicehub.resources.device.models.Computer.components`.
    """
    target.components.clear()
    for device in target.devices - {device}:
        if isinstance(device, Computer):
            target.components |= device.components


@event.listens_for(EraseBasic.device, Events.set.__name__, propagate=True)
@event.listens_for(Test.device, Events.set.__name__, propagate=True)
@event.listens_for(Install.device, Events.set.__name__, propagate=True)
@event.listens_for(Benchmark.device, Events.set.__name__, propagate=True)
def update_parent(target: Union[EraseBasic, Test, Install], device: Device, _, __):
    """
    Syncs the :attr:`Event.parent` with the parent of the device.
    """
    target.parent = None
    if isinstance(device, Component):
        target.parent = device.parent
