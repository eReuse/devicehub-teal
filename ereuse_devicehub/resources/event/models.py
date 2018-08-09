from collections import Iterable
from datetime import datetime, timedelta
from typing import Set, Union
from uuid import uuid4

from flask import current_app as app, g
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, Enum as DBEnum, \
    Float, ForeignKey, Interval, JSON, Numeric, SmallInteger, Unicode, event, orm
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.orm.events import AttributeEvents as Events
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent.models import Agent
from ereuse_devicehub.resources.device.models import Component, Computer, DataStorage, Desktop, \
    Device, Laptop, Server
from ereuse_devicehub.resources.enums import AppearanceRange, BOX_RATE_3, BOX_RATE_5, Bios, \
    FunctionalityRange, PriceSoftware, RATE_NEGATIVE, RATE_POSITIVE, RatingRange, RatingSoftware, \
    ReceiverRole, SnapshotExpectedEvents, SnapshotSoftware, TestHardDriveLength
from ereuse_devicehub.resources.image.models import Image
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE, STR_SM_SIZE, Thing
from ereuse_devicehub.resources.user.models import User
from teal.db import ArrayOfEnum, CASCADE, CASCADE_OWN, INHERIT_COND, IP, POLYMORPHIC_ID, \
    POLYMORPHIC_ON, StrictVersionType, URL, check_range
from teal.enums import Country, Currency, Subdivision
from teal.marshmallow import ValidationError

"""
A quantity of money with a currency.
"""


class JoinedTableMixin:
    # noinspection PyMethodParameters
    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), ForeignKey(Event.id), primary_key=True)


class Event(Thing):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    type = Column(Unicode, nullable=False)
    name = Column(Unicode(STR_BIG_SIZE), default='', nullable=False)
    name.comment = """
        A name or title for the event. Used when searching for events.
    """
    incidence = Column(Boolean, default=False, nullable=False)
    incidence.comment = """
        Should this event be reviewed due some anomaly?
    """
    closed = Column(Boolean, default=False, nullable=False)
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
    start_time = Column(db.TIMESTAMP(timezone=True))
    start_time.comment = """
       When the action starts. For some actions like reservations 
       the time when they are available, for others like renting
       when the renting starts.
    """
    end_time = Column(db.TIMESTAMP(timezone=True))
    end_time.comment = """
        When the action ends. For some actions like reservations
        the time when they expire, for others like renting
        the time the end rents. For punctual actions it is the time 
        they are performed; it differs with ``created`` in which
        created is the where the system received the action.
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
    # todo compute the org
    author = relationship(User,
                          backref=backref('authored_events', lazy=True, collection_class=set),
                          primaryjoin=author_id == User.id)
    author_id.comment = """
    The user that recorded this action in the system.
     
    This does not necessarily has to be the person that produced
    the action in the real world. For that purpose see
    ``agent``.
    """

    agent_id = Column(UUID(as_uuid=True),
                      ForeignKey(Agent.id),
                      nullable=False,
                      default=lambda: g.user.individual.id)
    # todo compute the org
    agent = relationship(Agent,
                         backref=backref('events_agent',
                                         lazy=True,
                                         collection_class=OrderedSet,
                                         order_by=lambda: Event.created),
                         primaryjoin=agent_id == Agent.id)
    agent_id.comment = """
    The direct performer or driver of the action. e.g. John wrote a book.
    
    It can differ with the user that registered the action in the
    system, which can be in their behalf.
    """

    components = relationship(Component,
                              backref=backref('events_components',
                                              lazy=True,
                                              order_by=lambda: Event.created,
                                              collection_class=OrderedSet),
                              secondary=lambda: EventComponent.__table__,
                              order_by=lambda: Component.id,
                              collection_class=OrderedSet)
    components.comment = """
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
    parent_id.comment = """
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

    @validates('end_time')
    def validate_end_time(self, _, end_time: datetime):
        if self.start_time and end_time <= self.start_time:
            raise ValidationError('The event cannot finish before it starts.')
        return end_time

    @validates('start_time')
    def validate_start_time(self, _, start_time: datetime):
        if self.end_time and start_time >= self.end_time:
            raise ValidationError('The event cannot start after it finished.')
        return start_time


class EventComponent(db.Model):
    device_id = Column(BigInteger, ForeignKey(Component.id), primary_key=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey(Event.id), primary_key=True)


class JoinedWithOneDeviceMixin:
    # noinspection PyMethodParameters
    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), ForeignKey(EventWithOneDevice.id), primary_key=True)


class EventWithOneDevice(JoinedTableMixin, Event):
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


class EraseBasic(JoinedWithOneDeviceMixin, EventWithOneDevice):
    zeros = Column(Boolean, nullable=False)
    zeros.comment = """
        Whether this erasure had a first erasure step consisting of
        only writing zeros.
    """


class EraseSectors(EraseBasic):
    pass


class Step(db.Model):
    erasure_id = Column(UUID(as_uuid=True), ForeignKey(EraseBasic.id), primary_key=True)
    type = Column(Unicode(STR_SM_SIZE), nullable=False)
    num = Column(SmallInteger, primary_key=True)
    error = Column(Boolean, default=False, nullable=False)
    start_time = Column(DateTime, nullable=False)
    start_time.comment = Event.start_time.comment
    end_time = Column(DateTime, CheckConstraint('end_time > start_time'), nullable=False)
    end_time.comment = Event.end_time.comment

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


class Snapshot(JoinedWithOneDeviceMixin, EventWithOneDevice):
    uuid = Column(UUID(as_uuid=True), unique=True)
    version = Column(StrictVersionType(STR_SM_SIZE), nullable=False)
    software = Column(DBEnum(SnapshotSoftware), nullable=False)
    elapsed = Column(Interval)
    elapsed.comment = """
        For Snapshots made with Workbench, the total amount of time
        it took to complete.
    """
    expected_events = Column(ArrayOfEnum(DBEnum(SnapshotExpectedEvents)))


class Install(JoinedWithOneDeviceMixin, EventWithOneDevice):
    elapsed = Column(Interval, nullable=False)


class SnapshotRequest(db.Model):
    id = Column(UUID(as_uuid=True), ForeignKey(Snapshot.id), primary_key=True)
    request = Column(JSON, nullable=False)
    snapshot = relationship(Snapshot,
                            backref=backref('request',
                                            lazy=True,
                                            uselist=False,
                                            cascade=CASCADE_OWN))


class Rate(JoinedWithOneDeviceMixin, EventWithOneDevice):
    rating = Column(Float(decimal_return_scale=2), check_range('rating', *RATE_POSITIVE))
    software = Column(DBEnum(RatingSoftware))
    version = Column(StrictVersionType)
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

    # todo ensure for WorkbenchRate version and software are not None when inserting them

    def ratings(self) -> Set['WorkbenchRate']:
        """
        Computes all the possible rates taking this rating as a model.

        Returns a set of ratings, including this one, which is mutated.
        """
        from ereuse_rate.main import main
        return main(self, **app.config.get_namespace('WORKBENCH_RATE_'))


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


class Price(JoinedWithOneDeviceMixin, EventWithOneDevice):
    currency = Column(DBEnum(Currency), nullable=False)
    price = Column(Numeric(precision=19, scale=4), check_range('price', 0), nullable=False)
    software = Column(DBEnum(PriceSoftware))
    version = Column(StrictVersionType)
    rating_id = Column(UUID(as_uuid=True), ForeignKey(AggregateRate.id))
    rating = relationship(AggregateRate,
                          backref=backref('price',
                                          lazy=True,
                                          cascade=CASCADE_OWN,
                                          uselist=False),
                          primaryjoin=AggregateRate.id == rating_id)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.currency = self.currency or app.config['PRICE_CURRENCY']


class EreusePrice(Price):
    """A Price class that auto-computes its amount by"""
    MULTIPLIER = {
        Desktop: 20,
        Laptop: 30
    }

    class Type:
        def __init__(self, percentage, price) -> None:
            # see https://stackoverflow.com/a/29651462 for the - 0.005
            self.amount = round(price * percentage - 0.005, 2)
            self.percentage = round(percentage - 0.005, 2)

    class Service:
        REFURBISHER, PLATFORM, RETAILER = 0, 1, 2
        STANDARD, WARRANTY2 = 'STD', 'WR2'
        SCHEMA = {
            Desktop: {
                RatingRange.HIGH: {
                    STANDARD: (0.35125, 0.204375, 0.444375),
                    WARRANTY2: (0.47425, 0.275875, 0.599875)
                },
                RatingRange.MEDIUM: {
                    STANDARD: (0.385, 0.2558333333, 0.3591666667),
                    WARRANTY2: (0.539, 0.3581666667, 0.5028333333)
                },
                RatingRange.LOW: {
                    STANDARD: (0.5025, 0.30875, 0.18875),
                },
            },
            Laptop: {
                RatingRange.HIGH: {
                    STANDARD: (0.3469230769, 0.195, 0.4580769231),
                    WARRANTY2: (0.4522307692, 0.2632307692, 0.6345384615)
                },
                RatingRange.MEDIUM: {
                    STANDARD: (0.382, 0.1735, 0.4445),
                    WARRANTY2: (0.5108, 0.2429, 0.6463)
                },
                RatingRange.LOW: {
                    STANDARD: (0.4528571429, 0.2264285714, 0.3207142857),
                }
            }
        }
        SCHEMA[Server] = SCHEMA[Desktop]

        def __init__(self, device, rating_range, role, price) -> None:
            cls = device.__class__ if device.__class__ != Server else Desktop
            rate = self.SCHEMA[cls][rating_range]
            self.standard = EreusePrice.Type(rate['STD'][role], price)
            self.warranty2 = EreusePrice.Type(rate['WR2'][role], price)

    def __init__(self, rating: AggregateRate, **kwargs) -> None:
        if rating.rating_range == RatingRange.VERY_LOW:
            raise ValueError('Cannot compute price for Range.VERY_LOW')
        self.price = round(rating.rating * self.MULTIPLIER[rating.device.__class__], 2)
        super().__init__(rating=rating, device=rating.device, **kwargs)
        self._compute()
        self.software = self.software or app.config['PRICE_SOFTWARE']
        self.version = self.version or app.config['PRICE_VERSION']

    @orm.reconstructor
    def _compute(self):
        """
        Calculates eReuse.org prices when initializing the
        instance from the price and other properties.
        """
        self.refurbisher = self._service(self.Service.REFURBISHER)
        self.retailer = self._service(self.Service.RETAILER)
        self.platform = self._service(self.Service.PLATFORM)
        self.warranty2 = round(self.refurbisher.warranty2.amount
                               + self.retailer.warranty2.amount
                               + self.platform.warranty2.amount, 2)

    def _service(self, role):
        return self.Service(self.device, self.rating.rating_range, role, self.price)


class Test(JoinedWithOneDeviceMixin, EventWithOneDevice):
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
    lifetime = Column(Interval)
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

    @validates('elapsed')
    def is_minute_and_bigger_than_1_minute(self, _, value: timedelta):
        seconds = value.total_seconds()
        assert not bool(seconds % 60)
        assert seconds >= 60
        return value


class Benchmark(JoinedWithOneDeviceMixin, EventWithOneDevice):
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


class ToRepair(EventWithMultipleDevices):
    pass


class Repair(EventWithMultipleDevices):
    pass


class ReadyToUse(EventWithMultipleDevices):
    pass


class ToPrepare(EventWithMultipleDevices):
    pass


class Prepare(EventWithMultipleDevices):
    pass


class Live(JoinedWithOneDeviceMixin, EventWithOneDevice):
    ip = Column(IP, nullable=False,
                comment='The IP where the live was triggered.')
    subdivision_confidence = Column(SmallInteger,
                                    check_range('subdivision_confidence', 0, 100),
                                    nullable=False)
    subdivision = Column(DBEnum(Subdivision), nullable=False)
    city = Column(Unicode(STR_SM_SIZE), nullable=False)
    city_confidence = Column(SmallInteger,
                             check_range('city_confidence', 0, 100),
                             nullable=False)
    isp = Column(Unicode(length=STR_SM_SIZE), nullable=False)
    organization = Column(Unicode(length=STR_SIZE))
    organization_type = Column(Unicode(length=STR_SM_SIZE))

    @property
    def country(self) -> Country:
        return self.subdivision.country
    # todo relate to snapshot
    # todo testing


class Organize(JoinedTableMixin, EventWithMultipleDevices):
    pass


class Reserve(Organize):
    pass


class CancelReservation(Organize):
    pass


class Trade(JoinedTableMixin, EventWithMultipleDevices):
    shipping_date = Column(DateTime)
    shipping_date.comment = """
            When are the devices going to be ready for shipping?
        """
    invoice_number = Column(Unicode(length=STR_SIZE))
    invoice_number.comment = """
            The id of the invoice so they can be linked.
        """
    price_id = Column(UUID(as_uuid=True), ForeignKey(Price.id))
    price = relationship(Price,
                         backref=backref('trade', lazy=True, uselist=False),
                         primaryjoin=price_id == Price.id)
    price_id.comment = """
            The price set for this trade.
            
            If no price is set it is supposed that the trade was
            not payed, usual in donations.
        """
    to_id = Column(UUID(as_uuid=True),
                   ForeignKey(Agent.id),
                   nullable=False,
                   default=lambda: g.user.id)
    # todo compute the org
    to = relationship(Agent,
                      backref=backref('events_to',
                                      lazy=True,
                                      collection_class=OrderedSet,
                                      order_by=lambda: Event.created),
                      primaryjoin=to_id == Agent.id)
    confirms_id = Column(UUID(as_uuid=True), ForeignKey(Organize.id))
    confirms = relationship(Organize,
                            backref=backref('confirmation', lazy=True, uselist=False),
                            primaryjoin=confirms_id == Organize.id)
    confirms_id.comment = """
            An organize action that this association confirms.
            
            For example, a ``Sell`` or ``Rent``
            can confirm a ``Reserve`` action.
        """


class Sell(Trade):
    pass


class Donate(Trade):
    pass


class Rent(Trade):
    pass


class CancelTrade(Trade):
    pass


class ToDisposeProduct(Trade):
    pass


class DisposeProduct(Trade):
    pass


class Receive(JoinedTableMixin, EventWithMultipleDevices):
    role = Column(DBEnum(ReceiverRole),
                  nullable=False,
                  default=ReceiverRole.Intermediary)


class Migrate(JoinedTableMixin, EventWithMultipleDevices):
    other = Column(URL(), nullable=False)
    other.comment = """
        The URL of the Migrate in the other end.
    """


class MigrateTo(Migrate):
    pass


class MigrateFrom(Migrate):
    pass


# Listeners
# Listeners validate values and keep relationships synced

# The following listeners avoids setting values to events that
# do not make sense. For example, EraseBasic to a graphic card.

@event.listens_for(TestDataStorage.device, Events.set.__name__, propagate=True)
@event.listens_for(Install.device, Events.set.__name__, propagate=True)
@event.listens_for(EraseBasic.device, Events.set.__name__, propagate=True)
def validate_device_is_data_storage(target: Event, value: DataStorage, old_value, initiator):
    """Validates that the device for data-storage events is effectively a data storage."""
    if value and not isinstance(value, DataStorage):
        raise TypeError('{} must be a DataStorage but you passed {}'.format(initiator.impl, value))


@event.listens_for(BenchmarkRamSysbench.device, Events.set.__name__, propagate=True)
def events_not_for_components(target: Event, value: Device, old_value, initiator):
    """Validates events that cannot be performed to components."""
    if isinstance(value, Component):
        raise TypeError('{!r} cannot be performed to a component ({!r}).'.format(target, value))


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
