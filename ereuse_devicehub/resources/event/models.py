from collections import Iterable
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_UP
from distutils.version import StrictVersion
from typing import Optional, Set, Union
from uuid import uuid4

import inflection
import teal.db
from boltons import urlutils
from citext import CIText
from flask import current_app as app, g
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Enum as DBEnum, \
    Float, ForeignKey, Integer, Interval, JSON, Numeric, SmallInteger, Unicode, event, orm
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.orm.events import AttributeEvents as Events
from sqlalchemy.util import OrderedSet
from teal.db import ArrayOfEnum, CASCADE_OWN, INHERIT_COND, IP, POLYMORPHIC_ID, \
    POLYMORPHIC_ON, StrictVersionType, URL, check_lower, check_range
from teal.enums import Country, Currency, Subdivision
from teal.marshmallow import ValidationError
from teal.resource import url_for_resource

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent.models import Agent
from ereuse_devicehub.resources.device.models import Component, Computer, DataStorage, Desktop, \
    Device, Laptop, Server
from ereuse_devicehub.resources.enums import AppearanceRange, Bios, ErasureStandards, \
    FunctionalityRange, PhysicalErasureMethod, PriceSoftware, RATE_NEGATIVE, RATE_POSITIVE, \
    RatingRange, RatingSoftware, ReceiverRole, Severity, SnapshotExpectedEvents, SnapshotSoftware, \
    TestDataStorageLength, FUNCTIONALITY_RANGE, FunctionalityRangev2
from ereuse_devicehub.resources.event.rate.workbench.v2_0 import QualityRate, FunctionalityRate
from ereuse_devicehub.resources.models import STR_SM_SIZE, Thing
from ereuse_devicehub.resources.user.models import User


class JoinedTableMixin:
    # noinspection PyMethodParameters
    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), ForeignKey(Event.id), primary_key=True)


class Event(Thing):
    """Event performed on a device.

    This class extends `Schema's Action <https://schema.org/Action>`_.
    """
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    type = Column(Unicode, nullable=False)
    name = Column(CIText(), default='', nullable=False)
    name.comment = """
        A name or title for the event. Used when searching for events.
    """
    severity = Column(teal.db.IntEnum(Severity), default=Severity.Info, nullable=False)
    severity.comment = Severity.__doc__
    closed = Column(Boolean, default=True, nullable=False)
    closed.comment = """
        Whether the author has finished the event.
        After this is set to True, no modifications are allowed.
        By default events are closed when performed.
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

    __table_args__ = (
        db.Index('ix_id', id, postgresql_using='hash'),
        db.Index('ix_type', type, postgresql_using='hash'),
        db.Index('ix_parent_id', parent_id, postgresql_using='hash')
    )

    @property
    def elapsed(self):
        """Returns the elapsed time with seconds precision."""
        t = self.end_time - self.start_time
        return timedelta(seconds=t.seconds)

    @property
    def url(self) -> urlutils.URL:
        """The URL where to GET this event."""
        return urlutils.URL(url_for_resource(Event, item_id=self.id))

    @property
    def certificate(self) -> Optional[urlutils.URL]:
        return None

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
        # noinspection PyUnresolvedReferences
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

    @property
    def date_str(self):
        return '{:%c}'.format(self.end_time or self.created)

    def __str__(self) -> str:
        return '{}'.format(self.severity)

    def __repr__(self):
        return '<{0.t} {0.id} {0.severity}>'.format(self)


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
                                          cascade=CASCADE_OWN,
                                          order_by=lambda: EventWithOneDevice.created,
                                          collection_class=OrderedSet),
                          primaryjoin=Device.id == device_id)

    __table_args__ = (
        db.Index('event_one_device_id_index', device_id, postgresql_using='hash'),
    )

    def __repr__(self) -> str:
        return '<{0.t} {0.id} {0.severity} device={0.device!r}>'.format(self)

    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'EventWithOneDevice':
            args[POLYMORPHIC_ON] = cls.type
        return args


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
        return '<{0.t} {0.id} {0.severity} devices={0.devices!r}>'.format(self)


class EventDevice(db.Model):
    device_id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey(EventWithMultipleDevices.id),
                      primary_key=True)


class Add(EventWithOneDevice):
    """The act of adding components to a device.

    It is usually used internally from a :class:`.Snapshot`, for
    example, when adding a secondary data storage to a computer.
    """


class Remove(EventWithOneDevice):
    """The act of removing components from a device.

    It is usually used internally from a :class:`.Snapshot`, for
    example, when removing a component from a broken computer.
    """


class Allocate(JoinedTableMixin, EventWithMultipleDevices):
    to_id = Column(UUID, ForeignKey(User.id))
    to = relationship(User, primaryjoin=User.id == to_id)
    organization = Column(CIText())


class Deallocate(JoinedTableMixin, EventWithMultipleDevices):
    from_id = Column(UUID, ForeignKey(User.id))
    from_rel = relationship(User, primaryjoin=User.id == from_id)
    organization = Column(CIText())


class EraseBasic(JoinedWithOneDeviceMixin, EventWithOneDevice):
    """An erasure attempt to a ``DataStorage``. The event contains
    information about success and nature of the erasure.

    EraseBasic is a software-based fast non-100%-secured way of
    erasing data storage, performed
    by Workbench Computer when executing the open-source
    `shred <https://en.wikipedia.org/wiki/Shred_(Unix)>`_.

    Users can generate erasure certificates from successful erasures.

    Erasures are an accumulation of **erasure steps**, that are performed
    as separate actions, called ``StepRandom``, for an erasure step
    that has overwritten data with random bits, and ``StepZero``,
    for an erasure step that has overwritten data with zeros.

    Erasure standards define steps and methodologies to use.
    Devicehub automatically shows the standards that each erasure
    follows.
    """
    method = 'Shred'
    """The method or software used to destroy the data."""

    @property
    def standards(self):
        """A set of standards that this erasure follows."""
        return ErasureStandards.from_data_storage(self)

    @property
    def certificate(self):
        """The URL of this erasure certificate."""
        # todo will this url_for_resoure work for other resources?
        return urlutils.URL(url_for_resource('Document', item_id=self.id))

    def __str__(self) -> str:
        return '{} on {}.'.format(self.severity, self.date_str)

    def __format__(self, format_spec: str) -> str:
        v = ''
        if 't' in format_spec:
            v += '{} {}'.format(self.type, self.severity)
        if 't' in format_spec and 's' in format_spec:
            v += '. '
        if 's' in format_spec:
            if self.standards:
                std = 'with standards {}'.format(self.standards)
            else:
                std = 'no standard'
            v += 'Method used: {}, {}. '.format(self.method, std)
            if self.end_time and self.start_time:
                v += '{} elapsed. '.format(self.elapsed)

            v += 'On {}'.format(self.date_str)
        return v


class EraseSectors(EraseBasic):
    """A secured-way of erasing data storages, checking sector-by-sector
    the erasure, using `badblocks <https://en.wikipedia.org/wiki/Badblocks>`_.
    """
    method = 'Badblocks'


class ErasePhysical(EraseBasic):
    """The act of physically destroying a data storage unit."""
    method = Column(DBEnum(PhysicalErasureMethod))


class Step(db.Model):
    erasure_id = Column(UUID(as_uuid=True), ForeignKey(EraseBasic.id), primary_key=True)
    type = Column(Unicode(STR_SM_SIZE), nullable=False)
    num = Column(SmallInteger, primary_key=True)
    severity = Column(teal.db.IntEnum(Severity), default=Severity.Info, nullable=False)
    start_time = Column(db.TIMESTAMP(timezone=True), nullable=False)
    start_time.comment = Event.start_time.comment
    end_time = Column(db.TIMESTAMP(timezone=True), CheckConstraint('end_time > start_time'),
                      nullable=False)
    end_time.comment = Event.end_time.comment

    erasure = relationship(EraseBasic,
                           backref=backref('steps',
                                           cascade=CASCADE_OWN,
                                           order_by=num,
                                           collection_class=ordering_list('num')))

    @property
    def elapsed(self):
        """Returns the elapsed time with seconds precision."""
        t = self.end_time - self.start_time
        return timedelta(seconds=t.seconds)

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

    def __format__(self, format_spec: str) -> str:
        return '{} – {} {}'.format(self.severity, self.type, self.elapsed)


class StepZero(Step):
    pass


class StepRandom(Step):
    pass


class Snapshot(JoinedWithOneDeviceMixin, EventWithOneDevice):
    """The Snapshot sets the physical information of the device (S/N, model...)
    and updates it with erasures, benchmarks, ratings, and tests; updates the
    composition of its components (adding / removing them), and links tags
    to the device.

    When receiving a Snapshot, the DeviceHub creates, adds and removes
    components to match the Snapshot. For example, if a Snapshot of a computer
    contains a new component, the system searches for the component in its
    database and, if not found, its creates it; finally linking it to the
    computer.

    A Snapshot is used with Remove to represent changes in components for
    a device:

    1. ``Snapshot`` creates a device if it does not exist, and the same
       for its components. This is all done in one ``Snapshot``.
    2. If the device exists, it updates its component composition by
       *adding* and *removing* them. If,
       for example, this new Snasphot doesn't have a component, it means that
       this component is not present anymore in the device, thus removing it
       from it. Then we have that:

         - Components that are added to the device: snapshot2.components -
           snapshot1.components
         - Components that are removed to the device: snapshot1.components -
           snapshot2.components

       When adding a component, there may be the case this component existed
       before and it was inside another device. In such case, DeviceHub will
       perform ``Remove`` on the old parent.

    **Snapshots from Workbench**

    When processing a device from the Workbench, this one performs a Snapshot
    and then performs more events (like testings, benchmarking...).

    There are two ways of sending this information. In an async way,
    this is, submitting events as soon as Workbench performs then, or
    submitting only one Snapshot event with all the other events embedded.

    **Asynced**

    The use case, which is represented in the ``test_workbench_phases``,
    is as follows:

    1. In **T1**, WorkbenchServer (as the middleware from Workbench and
       Devicehub) submits:

       - A ``Snapshot`` event with the required information to **synchronize**
         and **rate** the device. This is:

           - Identification information about the device and components
             (S/N, model, physical characteristics...)
           - ``Tags`` in a ``tags`` property in the ``device``.
           - ``Rate`` in an ``events`` property in the ``device``.
           - ``Benchmarks`` in an ``events`` property in each ``component``
             or ``device``.
           - ``TestDataStorage`` as in ``Benchmarks``.
       - An ordered set of **expected events**, defining which are the next
         events that Workbench will perform to the device in ideal
         conditions (device doesn't fail, no Internet drop...).

       Devicehub **syncs** the device with the database and perform the
       ``Benchmark``, the ``TestDataStorage``, and finally the ``Rate``.
       This leaves the Snapshot **open** to wait for the next events
       to come.
    2. Assuming that we expect all events, in **T2**, WorkbenchServer
       submits a ``StressTest`` with a ``snapshot`` field containing the
       ID of the Snapshot in 1, and Devicehub links the event with such
       ``Snapshot``.
    3. In **T3**, WorkbenchServer submits the ``Erase`` with the ``Snapshot``
       and ``component`` IDs from 1, linking it to them. It repeats
       this for all the erased data storage devices; **T3+Tn** being
       *n* the erased data storage devices.
    4. WorkbenchServer does like in 3. but for the event ``Install``,
       finishing in **T3+Tn+Tx**, being *x* the number of data storage
       devices with an OS installed into.
    5. In **T3+Tn+Tx**, when all *expected events* have been performed,
       Devicehub **closes** the ``Snapshot`` from 1.

    **Synced**

    Optionally, Devicehub understands receiving a ``Snapshot`` with all
    the events in an ``events`` property inside each affected ``component``
    or ``device``.
    """
    uuid = Column(UUID(as_uuid=True), unique=True)
    version = Column(StrictVersionType(STR_SM_SIZE), nullable=False)
    software = Column(DBEnum(SnapshotSoftware), nullable=False)
    elapsed = Column(Interval)
    elapsed.comment = """
        For Snapshots made with Workbench, the total amount of time
        it took to complete.
    """
    expected_events = Column(ArrayOfEnum(DBEnum(SnapshotExpectedEvents)))

    def __str__(self) -> str:
        return '{}. {} version {}.'.format(self.severity, self.software, self.version)


class Install(JoinedWithOneDeviceMixin, EventWithOneDevice):
    """The action of installing an Operative System to a data
    storage unit.
    """
    elapsed = Column(Interval, nullable=False)
    address = Column(SmallInteger, check_range('address', 8, 256))


class SnapshotRequest(db.Model):
    id = Column(UUID(as_uuid=True), ForeignKey(Snapshot.id), primary_key=True)
    request = Column(JSON, nullable=False)
    snapshot = relationship(Snapshot,
                            backref=backref('request',
                                            lazy=True,
                                            uselist=False,
                                            cascade=CASCADE_OWN))


class Rate(JoinedWithOneDeviceMixin, EventWithOneDevice):
    """The act of grading the appearance, performance, and functionality
    of a device.

    There are two base **types** of ``Rate``: ``WorkbenchRate``,
    ``ManualRate``. ``WorkbenchRate`` can have different
    **software** algorithms, and each software algorithm can have several
    **versions**. So, we have 3 dimensions for ``WorkbenchRate``:
    type, software, version.

    Devicehub generates a rate event for each software and version. So,
    if an agent fulfills a ``WorkbenchRate`` and there are 2 software
    algorithms and each has two versions, Devicehub will generate 4 rates.
    Devicehub understands that only one software and version are the
    **official** (set in the settings of each inventory),
    and it will generate an ``AggregateRating`` for only the official
    versions. At the same time, ``Price`` only computes the price of
    the **official** version.

    There are two ways of rating a device:

    1. When processing the device with Workbench and the Android App.
    2. Anytime after with the Android App or website.

    Refer to *processes* in the documentation to get more info with
    the process.

    The technical Workflow in Devicehub is as follows:

    1. In **T1**, the agent performs a ``Snapshot`` by processing the device
       through the Workbench. From the benchmarks and the visual and
       functional ratings the agent does in the device, the system generates
       many ``WorkbenchRate`` (as many as software and versions defined).
       With only this information, the system generates an ``AggregateRating``,
       which is the event that the user will see in the web.
    2. In **T2**, the agent can optionally visually re-rate the device
       using the mobile app, generating an ``AppRate``. This new
       action generates a new ``AggregateRating`` with the ``AppRate``
       plus the ``WorkbenchRate`` from 1.
    """
    rating = Column(Float(decimal_return_scale=2), check_range('rating', *RATE_POSITIVE))
    rating.comment = """The rating for the content."""
    software = Column(DBEnum(RatingSoftware))
    software.comment = """The algorithm used to produce this rating."""
    version = Column(StrictVersionType)
    version.comment = """The version of the software."""
    appearance = Column(Float(decimal_return_scale=2), check_range('appearance', *RATE_NEGATIVE))
    functionality = Column(Float(decimal_return_scale=2),
                           check_range('functionality', *RATE_NEGATIVE))

    @property
    def rating_range(self) -> RatingRange:
        if self.rating:
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

    def __str__(self) -> str:
        return '{} ({} v.{})'.format(self.rating_range, self.software, self.version)


class IndividualRate(Rate):
    pass


class ManualRate(IndividualRate):
    id = Column(UUID(as_uuid=True), ForeignKey(Rate.id), primary_key=True)
    labelling = Column(Boolean)
    labelling.comment = """Sets if there are labels stuck that should
    be removed.
    """
    appearance_range = Column(DBEnum(AppearanceRange))
    appearance_range.comment = AppearanceRange.__doc__
    functionality_range = Column(DBEnum(FunctionalityRange))
    functionality_range.comment = FunctionalityRange.__doc__

    def __str__(self) -> str:
        return super().__str__() + '. Appearance {} and functionality {}'.format(
            self.appearance_range,
            self.functionality_range
        )

    def ratings(self):
        raise NotImplementedError()


class WorkbenchComputerRate(ManualRate):
    id = Column(UUID(as_uuid=True), ForeignKey(ManualRate.id), primary_key=True)
    processor = Column(Float(decimal_return_scale=2), check_range('processor', *RATE_POSITIVE))
    ram = Column(Float(decimal_return_scale=2), check_range('ram', *RATE_POSITIVE))
    data_storage = Column(Float(decimal_return_scale=2),
                          check_range('data_storage', *RATE_POSITIVE))
    graphic_card = Column(Float(decimal_return_scale=2),
                          check_range('graphic_card', *RATE_POSITIVE))
    bios = Column(Float(decimal_return_scale=2),
                  check_range('bios', *RATE_POSITIVE))
    bios_range = Column(DBEnum(Bios))
    bios_range.comment = Bios.__doc__

    # todo ensure for WorkbenchRate version and software are not None when inserting them

    def ratings(self):
        """
        Computes all the possible rates taking this rating as a model.

        Returns a set of ratings, including this one, which is mutated,
        and the final :class:`.AggregateRate`.
        """
        from ereuse_devicehub.resources.event.rate.main import main
        return main(self, **app.config.get_namespace('WORKBENCH_RATE_'))

    @property
    def data_storage_range(self):
        if self.data_storage:
            return RatingRange.from_score(self.data_storage)

    @property
    def ram_range(self):
        if self.ram:
            return RatingRange.from_score(self.ram)

    @property
    def processor_range(self):
        if self.processor:
            return RatingRange.from_score(self.processor)

    @property
    def graphic_card_range(self):
        if self.graphic_card:
            return RatingRange.from_score(self.graphic_card)


"""     QUALITY RATE CODE START HERE     """


class QualityRate(Rate):
    id = Column(UUID(as_uuid=True), ForeignKey(Rate.id), primary_key=True)
    processor = Column(Float(decimal_return_scale=2), check_range('processor', *RATE_POSITIVE),
                       comment='Is a test explain cpu component.')
    ram = Column(Float(decimal_return_scale=2), check_range('ram', *RATE_POSITIVE),
                 comment='RAM memory rate.')
    data_storage = Column(Float(decimal_return_scale=2), check_range('data_storage', *RATE_POSITIVE),
                          comment='Data storage rate, like HHD, SSD.')

    @property
    def ram_range(self):
        return self.workbench.ram_range

    @property
    def processor_range(self):
        return self.workbench.processor_range

    @property
    def display_range(self):
        return self.workbench.data_storage_range

    @property
    def data_storage_range(self):
        return self.workbench.data_storage_range

    @property
    def battery_range(self):
        return self.workbench.ram_range

    @property
    def camera_range(self):
        return self.workbench_mobile.camera_range

    @property
    def graphic_card_range(self):
        return self.workbench_mobil.graphic_card_range


class QualityRateComputer(QualityRate):
    id = Column(UUID(as_uuid=True), ForeignKey(QualityRate.id), primary_key=True)
    processor = Column(Float(decimal_return_scale=2), check_range('processor', *RATE_POSITIVE),
                       comment='Is a test explain cpu component.')
    ram = Column(Float(decimal_return_scale=2), check_range('ram', *RATE_POSITIVE),
                 comment='RAM memory rate.')
    data_storage = Column(Float(decimal_return_scale=2), check_range('data_storage', *RATE_POSITIVE),
                          comment='Data storage rate, like HHD, SSD.')

    graphic_card = Column(Float(decimal_return_scale=2), check_range('graphic_card', *RATE_POSITIVE),
                          comment='Graphic card score in performance, amount of memory and benchmark result')
    network_adapter = Column(Float(decimal_return_scale=2), check_range('network_adapter', *RATE_POSITIVE),
                             comment='Network adapter rate, take it speed limit')

    bios = Column(Float(decimal_return_scale=2), check_range('bios', *RATE_POSITIVE))
    bios_range = Column(DBEnum(Bios))
    bios_range.comment = Bios.__doc__

    # todo ensure for WorkbenchRate version and software are not None when inserting them

    def ratings(self):
        """
        #Computes all the possible rates taking this rating as a model.

        #Returns a set of ratings, including this one, which is mutated,
        #and the final :class:`.AggregateRate`.
        """
        from ereuse_devicehub.resources.event.rate.main import main
        return main(self, **app.config.get_namespace('WORKBENCH_RATE_'))

    @property
    def graphic_card_range(self):
        if self.graphic_card:
            return RatingRange.from_score(self.graphic_card)

    @property
    def network_adapter_range(self):
        return self.workbench_mobil.network_adapter_range

    @property
    def bios_range(self):
        return self.workbench_mobil.bios_range


class QualityRateMobile(QualityRate):
    id = Column(UUID(as_uuid=True), ForeignKey(QualityRate.id), primary_key=True)
    display = Column(Float(decimal_return_scale=2), check_range('display', *RATE_POSITIVE))
    display.comment = 'Display rate, screen resolution and size to calculate PPI and convert in score'
    battery = Column(Float(decimal_return_scale=2), check_range('battery', *RATE_POSITIVE),
                     comment='Battery rate is related with capacity and its health')
    camera = Column(Float(decimal_return_scale=2), check_range('camera', *RATE_POSITIVE),
                    comment='Camera rate take into account resolution')

    graphic_card = Column(Float(decimal_return_scale=2), check_range('graphic_card', *RATE_POSITIVE),
                          comment='Graphic card score in performance, amount of memory and benchmark result')
    network_adapter = Column(Float(decimal_return_scale=2), check_range('network_adapter', *RATE_POSITIVE),
                             comment='Network adapter rate, take it speed limit')

    bios = Column(Float(decimal_return_scale=2), check_range('bios', *RATE_POSITIVE))
    bios_range = Column(DBEnum(Bios))
    bios_range.comment = Bios.__doc__

    # todo ensure for WorkbenchRate version and software are not None when inserting them

    def ratings(self):
        """
        #Computes all the possible rates taking this rating as a model.
        """
        from ereuse_devicehub.resources.event.rate.main import main
        return main(self, **app.config.get_namespace('WORKBENCH_RATE_'))

    @property
    def display_range(self):
        if self.data_storage:
            return RatingRange.from_score(self.data_storage)

    @property
    def battery_range(self):
        if self.ram:
            return RatingRange.from_score(self.ram)

    @property
    def camera_range(self):
        if self.processor:
            return RatingRange.from_score(self.processor)

    @property
    def graphic_card_range(self):
        if self.graphic_card:
            return RatingRange.from_score(self.graphic_card)


class FunctionalityRate(Rate):
    id = Column(UUID(as_uuid=True), ForeignKey(Rate.id), primary_key=True)
    functionality = Column(Float(decimal_return_scale=2), check_range('functionality', *FUNCTIONALITY_RANGE))
    functionality.comment = 'Functionality rate of a device'

    functionality_range = Column(DBEnum(FunctionalityRangev2))
    functionality_range.comment = FunctionalityRangev2.__doc__

    connectivity = Column(Float(decimal_return_scale=2),
                          comment='This punctuation covers a series of aspects related to connectivity.')
    audio = Column(Float(decimal_return_scale=2), comment='Take into account loudspeaker and microphone')

    @property
    def connectivity_rate(self):
        yield

    @property
    def audio_rate(self):
        yield

    @property
    def test_buttonse(self):
        yield

    @classmethod
    def test_camera_defects(self):
        yield


class FinalRate(Rate):
    id = Column(UUID(as_uuid=True), ForeignKey(Rate.id), primary_key=True)


class AggregateRate(Rate):
    id = Column(UUID(as_uuid=True), ForeignKey(Rate.id), primary_key=True)
    manual_id = Column(UUID(as_uuid=True), ForeignKey(ManualRate.id))
    manual_id.comment = """The ManualEvent used to generate this
    aggregation, or None if none used.

    An example of ManualEvent is using the web or the Android app
    to rate a device.
    """
    manual = relationship(ManualRate,
                          backref=backref('aggregate_rate_manual',
                                          lazy=True,
                                          order_by=lambda: AggregateRate.created,
                                          collection_class=OrderedSet),
                          primaryjoin=manual_id == ManualRate.id)
    workbench_id = Column(UUID(as_uuid=True), ForeignKey(QualityRateComputer.id))
    workbench_id.comment = """The WorkbenchRate used to generate
    this aggregation, or None if none used.
    """
    workbench = relationship(QualityRateComputer,
                             backref=backref('aggregate_rate_workbench',
                                             lazy=True,
                                             order_by=lambda: AggregateRate.created,
                                             collection_class=OrderedSet),
                             primaryjoin=workbench_id == QualityRateComputer.id)

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault('version', StrictVersion('1.0'))
        super().__init__(*args, **kwargs)

    # todo take value from LAST event (manual or workbench)

    @property
    def processor(self):
        return self.workbench.processor

    @property
    def ram(self):
        return self.workbench.ram

    @property
    def data_storage(self):
        return self.workbench.data_storage

    @property
    def graphic_card(self):
        return self.workbench.graphic_card

    @property
    def data_storage_range(self):
        return self.workbench.data_storage_range

    @property
    def ram_range(self):
        return self.workbench.ram_range

    @property
    def processor_range(self):
        return self.workbench.processor_range

    @property
    def graphic_card_range(self):
        return self.workbench.graphic_card_range

    @property
    def bios(self):
        return self.workbench.bios

    @property
    def functionality_range(self):
        return self.workbench.functionality_range

    @property
    def appearance_range(self):
        return self.workbench.appearance_range

    @property
    def bios_range(self):
        return self.workbench.bios_range

    @property
    def labelling(self):
        return self.workbench.labelling

    @classmethod
    def from_workbench_rate(cls, rate: QualityRateComputer):
        aggregate = cls()
        aggregate.rating = rate.rating
        aggregate.software = rate.software
        aggregate.appearance = rate.appearance
        aggregate.functionality = rate.functionality
        aggregate.device = rate.device
        aggregate.workbench = rate
        return aggregate


####################################################################################


class ResultRate(Rate):
    """The act of grading the appearance, quality (performance), and functionality
        of a device.

        There are five categories of ``Rate``:
        1. ``Quality``. How good is the machine, in terms of performance.
        2. ``Functionality``.
        3. ``Appearance``.
        4. ``Market value``.
        5. ``Cost of repair``.


        There are types of rating a device:

        1. Rate Quality
        2. Rate Functionality
        3. Rate Final


        List of source where can input information of rating a device:

        1. When processing the device with Workbench Computer/Mobile.
        2. Using the Android App (through Scan).
        3.
        4. Anytime after manually written in a form in the website.
        """

    id = Column(UUID(as_uuid=True), ForeignKey(Rate.id), primary_key=True)
    quality_id = Column(UUID(as_uuid=True), ForeignKey(ManualRate.id))
    quality_id.comment = """The Quality Rate used to generate this
    aggregation, or None if none used.
    """

    func_id = Column(UUID(as_uuid=True), ForeignKey(ManualRate.id))
    func_id.comment = """The Functionality Rate used to generate this
      aggregation, or None if none used.
      """

    final_id = Column(UUID(as_uuid=True), ForeignKey(ManualRate.id))
    final_id.comment = """The Final Rate used to generate this
      aggregation, or None if none used.
      """

    """     MANUAL INPUT      """
    manual_id = Column(UUID(as_uuid=True), ForeignKey(ManualRate.id))
    manual_id.comment = """The ManualEvent used to generate this
      aggregation, or None if none used.

      An example of ManualEvent is using the web or the Android app
      to rate a device.
      """
    manual = relationship(ManualRate,
                          backref=backref('aggregate_rate_manual',
                                          lazy=True,
                                          order_by=lambda: ResultRate.created,
                                          collection_class=OrderedSet),
                          primaryjoin=manual_id == ManualRate.id)

    """     WORKBENCH COMPUTER       """
    workbench_computer_id = Column(UUID(as_uuid=True), ForeignKey(QualityRateComputer.id))
    workbench_computer_id.comment = """The WorkbenchRate used to generate
    this aggregation, or None if none used.
    """
    workbench_computer = relationship(QualityRateComputer,
                                      backref=backref('aggregate_rate_workbench',
                                                      lazy=True,
                                                      order_by=lambda: ResultRate.created,
                                                      collection_class=OrderedSet),
                                      primaryjoin=workbench_computer_id == QualityRateComputer.id)

    """     WORKBENCH MOBILE       """

    workbench_mobile_id = Column(UUID(as_uuid=True), ForeignKey(QualityRateMobile.id))
    workbench_mobile_id.comment = """The WorkbenchRate used to generate
    this aggregation, or None if none used.
    """
    workbench_mobile = relationship(QualityRateMobile,
                                    backref=backref('aggregate_rate_workbench',
                                                    lazy=True,
                                                    order_by=lambda: ResultRate.created,
                                                    collection_class=OrderedSet),
                                    primaryjoin=workbench_mobile_id == QualityRateMobile.id)

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault('version', StrictVersion('1.0'))
        super().__init__(*args, **kwargs)

    @classmethod
    def quality_rate(cls, quality: QualityRate):
        pass

    @classmethod
    def functionality_rate(cls, func: FunctionalityRate):
        pass

    @classmethod
    def final_rate(cls, rate: Rate):
        pass

    # Categories

    @classmethod
    def quality_category(cls, quality: QualityRate):
        pass

    @classmethod
    def functionality_category(cls, quality: QualityRate):
        pass

    @classmethod
    def appearance_category(cls, quality: QualityRate):
        pass

    @classmethod
    def maket_value_category(cls, quality: QualityRate):
        pass

    @classmethod
    def cost_of_repair_category(cls, quality: QualityRate):
        pass


    # todo take value from LAST event (manual or workbench)

    @property
    def processor(self):
        return self.workbench.processor

    @property
    def ram(self):
        return self.workbench.ram

    @property
    def data_storage(self):
        return self.workbench.data_storage

    @property
    def graphic_card(self):
        return self.workbench.graphic_card

    @property
    def data_storage_range(self):
        return self.workbench.data_storage_range

    @property
    def ram_range(self):
        return self.workbench.ram_range

    @property
    def processor_range(self):
        return self.workbench.processor_range

    @property
    def graphic_card_range(self):
        return self.workbench.graphic_card_range

    @property
    def bios(self):
        return self.workbench.bios

    @property
    def functionality_range(self):
        return self.workbench.functionality_range

    @property
    def appearance_range(self):
        return self.workbench.appearance_range

    @property
    def bios_range(self):
        return self.workbench.bios_range

    @property
    def labelling(self):
        return self.workbench.labelling

    @classmethod
    def from_workbench_rate(cls, rate: QualityRateComputer):
        aggregate = cls()
        aggregate.rating = rate.rating
        aggregate.software = rate.software
        aggregate.appearance = rate.appearance
        aggregate.functionality = rate.functionality
        aggregate.device = rate.device
        aggregate.workbench = rate
        return aggregate


class Price(JoinedWithOneDeviceMixin, EventWithOneDevice):
    """The act of setting a trading price for the device.

    This does not imply that the device is ultimately traded for that
    price. Use the :class:`.Sell` for that.

    Devicehub automatically computes a price from ``AggregateRating``
    events. As in a **Rate**, price can have **software** and **version**,
    and there is an **official** price that is used to automatically
    compute the price from an ``AggregateRating``. Only the official price
    is computed from an ``AggregateRating``.
    """
    SCALE = 4
    ROUND = ROUND_HALF_EVEN
    currency = Column(DBEnum(Currency), nullable=False)
    currency.comment = """The currency of this price as for ISO 4217."""
    price = Column(Numeric(precision=19, scale=SCALE), check_range('price', 0), nullable=False)
    price.comment = """The value."""
    software = Column(DBEnum(PriceSoftware))
    software.comment = """The software used to compute this price,
    if the price was computed automatically. This field is None
    if the price has been manually set.
    """
    version = Column(StrictVersionType)
    version.comment = """The version of the software, or None."""
    rating_id = Column(UUID(as_uuid=True), ForeignKey(AggregateRate.id))
    rating_id.comment = """The AggregateRate used to auto-compute
    this price, if it has not been set manually."""
    rating = relationship(AggregateRate,
                          backref=backref('price',
                                          lazy=True,
                                          cascade=CASCADE_OWN,
                                          uselist=False),
                          primaryjoin=AggregateRate.id == rating_id)

    def __init__(self, *args, **kwargs) -> None:
        if 'price' in kwargs:
            assert isinstance(kwargs['price'], Decimal), 'Price must be a Decimal'
        super().__init__(currency=kwargs.pop('currency', app.config['PRICE_CURRENCY']), *args,
                         **kwargs)

    @classmethod
    def to_price(cls, value: Union[Decimal, float], rounding=ROUND) -> Decimal:
        """Returns a Decimal value with the correct scale for Price.price."""
        if isinstance(value, float):
            value = Decimal(value)
        # equation from marshmallow.fields.Decimal
        return value.quantize(Decimal((0, (1,), -cls.SCALE)), rounding=rounding)

    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Price':
            args[POLYMORPHIC_ON] = cls.type
        return args

    def __str__(self) -> str:
        return '{0:0.2f} {1}'.format(self.price, self.currency)


class EreusePrice(Price):
    """The act of setting a price by guessing it using the eReuse.org
    algorithm.

    This algorithm states that the price is the use value of the device
    (represented by its last :class:`.Rate`) multiplied by a constants
    value agreed by a circuit or platform.
    """
    MULTIPLIER = {
        Desktop: 20,
        Laptop: 30
    }

    class Type:
        def __init__(self, percentage: float, price: Decimal) -> None:
            # see https://stackoverflow.com/a/29651462 for the - 0.005
            self.amount = EreusePrice.to_price(price * Decimal(percentage))
            self.percentage = EreusePrice.to_price(price * Decimal(percentage))
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

        def __init__(self, device, rating_range, role, price: Decimal) -> None:
            cls = device.__class__ if device.__class__ != Server else Desktop
            rate = self.SCHEMA[cls][rating_range]
            self.standard = EreusePrice.Type(rate[self.STANDARD][role], price)
            if self.WARRANTY2 in rate:
                self.warranty2 = EreusePrice.Type(rate[self.WARRANTY2][role], price)

    def __init__(self, rating: AggregateRate, **kwargs) -> None:
        if rating.rating_range == RatingRange.VERY_LOW:
            raise ValueError('Cannot compute price for Range.VERY_LOW')
        # We pass ROUND_UP strategy so price is always greater than what refurbisher... amounts
        price = self.to_price(rating.rating * self.MULTIPLIER[rating.device.__class__], ROUND_UP)
        super().__init__(rating=rating,
                         device=rating.device,
                         price=price,
                         software=kwargs.pop('software', app.config['PRICE_SOFTWARE']),
                         version=kwargs.pop('version', app.config['PRICE_VERSION']),
                         **kwargs)
        self._compute()

    @orm.reconstructor
    def _compute(self):
        """
        Calculates eReuse.org prices when initializing the
        instance from the price and other properties.
        """
        self.refurbisher = self._service(self.Service.REFURBISHER)
        self.retailer = self._service(self.Service.RETAILER)
        self.platform = self._service(self.Service.PLATFORM)
        if hasattr(self.refurbisher, 'warranty2'):
            self.warranty2 = round(self.refurbisher.warranty2.amount
                                   + self.retailer.warranty2.amount
                                   + self.platform.warranty2.amount, 2)

    def _service(self, role):
        return self.Service(self.device, self.rating.rating_range, role, self.price)


class Test(JoinedWithOneDeviceMixin, EventWithOneDevice):
    """The act of testing the physical condition of a device and its
    components.

    Testing errors and warnings are easily taken in
    :attr:`ereuse_devicehub.resources.device.models.Device.working`.
    """
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
    """
    The act of testing the data storage.

    Testing is done using the `S.M.A.R.T self test
    <https://en.wikipedia.org/wiki/S.M.A.R.T.#Self-tests>`_. Note
    that not all data storage units, specially some new PCIe ones, do not
    support SMART testing.

    The test takes to other SMART values indicators of the overall health
    of the data storage.
    """
    id = Column(UUID(as_uuid=True), ForeignKey(Test.id), primary_key=True)
    length = Column(DBEnum(TestDataStorageLength), nullable=False)  # todo from type
    status = Column(Unicode(), check_lower('status'), nullable=False)
    lifetime = Column(Interval)
    assessment = Column(Boolean)
    reallocated_sector_count = Column(SmallInteger)
    power_cycle_count = Column(SmallInteger)
    reported_uncorrectable_errors = Column(SmallInteger)
    command_timeout = Column(Integer)
    current_pending_sector_count = Column(SmallInteger)
    offline_uncorrectable = Column(SmallInteger)
    remaining_lifetime_percentage = Column(SmallInteger)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Define severity
        # As of https://www.backblaze.com/blog/hard-drive-smart-stats/ and
        # https://www.backblaze.com/blog-smart-stats-2014-8.html
        # We can guess some future disk failures by analyzing some SMART data.
        if self.severity is None:
            # Test finished successfully
            if not self.assessment:
                self.severity = Severity.Error
            elif self.current_pending_sector_count and self.current_pending_sector_count > 40 \
                    or self.reallocated_sector_count and self.reallocated_sector_count > 10:
                self.severity = Severity.Warning

    def __str__(self) -> str:
        t = inflection.humanize(self.status)
        if self.lifetime:
            t += ' with a lifetime of {:.1f} years.'.format(self.lifetime.days / 365)
        t += self.description
        return t


class StressTest(Test):
    """The act of stressing (putting to the maximum capacity)
    a device for an amount of minutes. If the device is not in great
    condition won't probably survive such test.
    """

    @validates('elapsed')
    def is_minute_and_bigger_than_1_minute(self, _, value: timedelta):
        seconds = value.total_seconds()
        assert not bool(seconds % 60)
        assert seconds >= 60
        return value

    def __str__(self) -> str:
        return '{}. Computing for {}'.format(self.severity, self.elapsed)


class Benchmark(JoinedWithOneDeviceMixin, EventWithOneDevice):
    """The act of gauging the performance of a device."""
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
    """Benchmarks the data storage unit reading and writing speeds."""
    id = Column(UUID(as_uuid=True), ForeignKey(Benchmark.id), primary_key=True)
    read_speed = Column(Float(decimal_return_scale=2), nullable=False)
    write_speed = Column(Float(decimal_return_scale=2), nullable=False)

    def __str__(self) -> str:
        return 'Read: {} MB/s, write: {} MB/s'.format(self.read_speed, self.write_speed)


class BenchmarkWithRate(Benchmark):
    """The act of benchmarking a device with a single rate."""
    id = Column(UUID(as_uuid=True), ForeignKey(Benchmark.id), primary_key=True)
    rate = Column(Float, nullable=False)

    def __str__(self) -> str:
        return '{} points'.format(self.rate)


class BenchmarkProcessor(BenchmarkWithRate):
    """Benchmarks a processor by executing `BogoMips
    <https://en.wikipedia.org/wiki/BogoMips>`_. Note that this is not
    a reliable way of rating processors and we keep it for compatibility
    purposes.
    """
    pass


class BenchmarkProcessorSysbench(BenchmarkProcessor):
    """Benchmarks a processor by using the processor benchmarking
    utility of `sysbench <https://github.com/akopytov/sysbench>`_.
    """


class BenchmarkRamSysbench(BenchmarkWithRate):
    pass


class ToRepair(EventWithMultipleDevices):
    """Select a device to be repaired."""


class Repair(EventWithMultipleDevices):
    """Repair is the act of performing reparations.

    If a repair without an error is performed,
    it represents that the reparation has been successful.
    """


class ReadyToUse(EventWithMultipleDevices):
    """The device is ready to be used.

    This involves greater preparation from the ``Prepare`` event,
    and users should only use a device after this event is performed.

    Users usually require devices with this event before shipping them
    to costumers.
    """


class ToPrepare(EventWithMultipleDevices):
    """The device has been selected for preparation.

    See Prepare for more info.

    Usually **ToPrepare** is the next event done after registering the
    device.
    """
    pass


class Prepare(EventWithMultipleDevices):
    """Work has been performed to the device to a defined point of
    acceptance.

    Users using this event have to agree what is this point
    of acceptance; for some is when the device just works, for others
    when some testing has been performed.
    """


class Live(JoinedWithOneDeviceMixin, EventWithOneDevice):
    """A keep-alive from a device connected to the Internet with
    information about its state (in the form of a ``Snapshot`` event)
     and usage statistics.
    """
    ip = Column(IP, nullable=False,
                comment='The IP where the live was triggered.')
    subdivision_confidence = Column(SmallInteger,
                                    check_range('subdivision_confidence', 0, 100),
                                    nullable=False)
    subdivision = Column(DBEnum(Subdivision), nullable=False)
    city = Column(Unicode(STR_SM_SIZE), check_lower('city'), nullable=False)
    city_confidence = Column(SmallInteger,
                             check_range('city_confidence', 0, 100),
                             nullable=False)
    isp = Column(Unicode(STR_SM_SIZE), check_lower('isp'), nullable=False)
    organization = Column(Unicode(STR_SM_SIZE), check_lower('organization'))
    organization_type = Column(Unicode(STR_SM_SIZE), check_lower('organization_type'))

    @property
    def country(self) -> Country:
        return self.subdivision.country
    # todo relate to snapshot
    # todo testing


class Organize(JoinedTableMixin, EventWithMultipleDevices):
    """The act of manipulating/administering/supervising/controlling
    one or more devices.
    """


class Reserve(Organize):
    """The act of reserving devices.

    After this event is performed, the user is the **reservee** of the
    devices. There can only be one non-cancelled reservation for
    a device, and a reservation can only have one reservee.
    """


class CancelReservation(Organize):
    """The act of cancelling a reservation."""


class Trade(JoinedTableMixin, EventWithMultipleDevices):
    """Trade actions log the political exchange of devices between users.
    Every time a trade event is performed, the old user looses its
    political possession, for example ownership, in favor of another
    user.


    Performing trade events changes the *Trading* state of the
    device —:class:`ereuse_devicehub.resources.device.states.Trading`.

    This class and its inheritors
    extend `Schema's Trade <http://schema.org/TradeAction>`_.
    """
    shipping_date = Column(db.TIMESTAMP(timezone=True))
    shipping_date.comment = """
            When are the devices going to be ready for shipping?
        """
    invoice_number = Column(CIText())
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
    to_id = Column(UUID(as_uuid=True), ForeignKey(Agent.id), nullable=False)
    # todo compute the org
    to = relationship(Agent,
                      backref=backref('events_to',
                                      lazy=True,
                                      collection_class=OrderedSet,
                                      order_by=lambda: Event.created),
                      primaryjoin=to_id == Agent.id)
    to_comment = """
        The agent that gets the device due this deal.
    """
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
    """The act of taking money from a buyer in exchange of a device."""


class Donate(Trade):
    """The act of giving devices without compensation."""


class Rent(Trade):
    """The act of giving money in return for temporary use, but not
    ownership, of a device.
    """


class CancelTrade(Trade):
    """The act of cancelling a `Sell`_, `Donate`_ or `Rent`_."""
    # todo cancelTrade does not do anything


class ToDisposeProduct(Trade):
    """The act of setting a device for being disposed.

    See :class:`.DisposeProduct`.
    """
    # todo test this


class DisposeProduct(Trade):
    """The act of getting rid of devices by giving (selling, donating)
    to another organization, like a waste manager.


    See :class:`.ToDispose` and :class:`.DisposeProduct` for
    disposing without trading the device. See :class:`.DisposeWaste`
    and :class:`.Recover` for disposing in-house, this is,
    without trading the device.
    """
    # todo For usability purposes, users might not directly perform
    #     *DisposeProduct*, but this could automatically be done when
    #     performing :class:`.ToDispose` + :class:`.Receive` to a
    #     ``RecyclingCenter``.


class Receive(JoinedTableMixin, EventWithMultipleDevices):
    """The act of physically taking delivery of a device.

    The receiver confirms that the devices have arrived, and thus,
    they are the
    :attr:`ereuse_devicehub.resources.device.models.Device.physical_possessor`.

    This differs from :class:`.Trade` in that trading changes the
    political possession. As an example, a transporter can *receive*
    a device but it is not it's owner. After the delivery, the
    transporter performs another *receive* to the final owner.

    The receiver can optionally take a
    :class:`ereuse_devicehub.resources.enums.ReceiverRole`.
    """
    role = Column(DBEnum(ReceiverRole),
                  nullable=False,
                  default=ReceiverRole.Intermediary)


class Migrate(JoinedTableMixin, EventWithMultipleDevices):
    """Moves the devices to a new database/inventory. Devices cannot be
    modified anymore at the previous database.
    """
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
