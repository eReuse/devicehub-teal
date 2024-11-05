"""This file contains all actions can apply to a device and is sorted according
to a structure based on:

* Generic Actions
* Benchmarks
* Tests
* Rates
* Prices

Within the above general classes are subclasses in A order.
"""

import copy
import hashlib
import json
import time
import logging

from collections import Iterable
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_EVEN, ROUND_UP, Decimal
from operator import itemgetter
from typing import Optional, Set, Union
from uuid import uuid4

import inflection
from boltons import urlutils
from citext import CIText
from dateutil.tz import tzutc
from ereuseapi.methods import API
from flask import current_app as app
from flask import g, session
from sortedcontainers import SortedSet
from sqlalchemy import JSON, BigInteger, Boolean, CheckConstraint, Column
from sqlalchemy import Enum as DBEnum
from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    Interval,
    Numeric,
    SmallInteger,
    Unicode,
    event,
    orm,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.orm.events import AttributeEvents as Events
from sqlalchemy.util import OrderedSet

import ereuse_devicehub.teal.db
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent.models import Agent
from ereuse_devicehub.resources.device.metrics import TradeMetrics
from ereuse_devicehub.resources.device.models import (
    Component,
    Computer,
    DataStorage,
    Desktop,
    Device,
    Laptop,
    Server,
)
from ereuse_devicehub.resources.enums import (
    R_NEGATIVE,
    R_POSITIVE,
    AppearanceRange,
    BatteryHealth,
    BiosAccessRange,
    ErasureStandards,
    FunctionalityRange,
    PhysicalErasureMethod,
    PriceSoftware,
    RatingRange,
    Severity,
    SnapshotSoftware,
    StatusCode,
    TestDataStorageLength,
)
from ereuse_devicehub.resources.models import STR_SM_SIZE, Thing
from ereuse_devicehub.resources.tradedocument.models import TradeDocument
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.teal.db import (
    CASCADE_OWN,
    INHERIT_COND,
    POLYMORPHIC_ID,
    POLYMORPHIC_ON,
    URL,
    StrictVersionType,
    check_lower,
    check_range,
)
from ereuse_devicehub.teal.enums import Currency
from ereuse_devicehub.teal.resource import url_for_resource


logger = logging.getLogger(__name__)


class JoinedTableMixin:
    # noinspection PyMethodParameters
    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), ForeignKey(Action.id), primary_key=True)


_sorted_actions = {'order_by': lambda: Action.end_time, 'collection_class': SortedSet}


def sorted_actions_by(data):
    return {'order_by': lambda: data, 'collection_class': SortedSet}


"""For db.backref, return the actions sorted by end_time."""


class Action(Thing):
    """Action performed on a device.

    This class extends `Schema's Action <https://schema.org/Action>`_.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    type = Column(Unicode, nullable=False)
    name = Column(CIText(), default='', nullable=False)
    name.comment = """A name or title for the action. Used when searching
    for actions.
    """
    severity = Column(
        ereuse_devicehub.teal.db.IntEnum(Severity),
        default=Severity.Info,
        nullable=False,
    )
    severity.comment = Severity.__doc__
    closed = Column(Boolean, default=True, nullable=False)
    closed.comment = """Whether the author has finished the action.
    After this is set to True, no modifications are allowed.
    By default actions are closed when performed.
    """
    description = Column(Unicode, default='', nullable=False)
    description.comment = """A comment about the action."""
    start_time = Column(db.TIMESTAMP(timezone=True))
    start_time.comment = """When the action starts. For some actions like
    reservations the time when they are available, for others like renting
    when the renting starts.
    """
    end_time = Column(db.TIMESTAMP(timezone=True))
    end_time.comment = """When the action ends. For some actions like reservations
    the time when they expire, for others like renting
    the time the end rents. For punctual actions it is the time
    they are performed; it differs with ``created`` in which
    created is the where the system received the action.
    """

    snapshot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('snapshot.id', use_alter=True, name='snapshot_actions'),
    )
    snapshot = relationship(
        'Snapshot',
        backref=backref('actions', lazy=True, cascade=CASCADE_OWN, **_sorted_actions),
        primaryjoin='Action.snapshot_id == Snapshot.id',
    )

    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    # todo compute the org
    author = relationship(
        User,
        backref=backref('authored_actions', lazy=True, collection_class=set),
        primaryjoin=author_id == User.id,
    )
    author_id.comment = """The user that recorded this action in the system.

    This does not necessarily has to be the person that produced
    the action in the real world. For that purpose see
    ``agent``.
    """

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey(Agent.id),
        nullable=False,
        default=lambda: g.user.individual.id,
    )
    # todo compute the org
    agent = relationship(
        Agent,
        backref=backref('actions_agent', lazy=True, **_sorted_actions),
        primaryjoin=agent_id == Agent.id,
    )
    agent_id.comment = """The direct performer or driver of the action. e.g. John wrote a book.

    It can differ with the user that registered the action in the
    system, which can be in their behalf.
    """

    components = relationship(
        Component,
        backref=backref('actions_components', lazy=True, **_sorted_actions),
        secondary=lambda: ActionComponent.__table__,
        order_by=lambda: Component.id,
        collection_class=OrderedSet,
    )
    components.comment = """The components that are affected by the action.

    When performing actions to parent devices their components are
    affected too.

    For example: an ``Allocate`` is performed to a Computer and this
    relationship is filled with the components the computer had
    at the time of the action.

    For Add and Remove though, this has another meaning: the components
    that are added or removed.
    """
    parent_id = Column(BigInteger, ForeignKey(Computer.id))
    parent = relationship(
        Computer,
        backref=backref('actions_parent', lazy=True, **_sorted_actions),
        primaryjoin=parent_id == Computer.id,
    )
    parent_id.comment = """For actions that are performed to components,
    the device parent at that time.

    For example: for a ``EraseBasic`` performed on a data storage, this
    would point to the computer that contained this data storage, if any.
    """

    __table_args__ = (
        db.Index('ix_id', id, postgresql_using='hash'),
        db.Index('ix_type', type, postgresql_using='hash'),
        db.Index('ix_parent_id', parent_id, postgresql_using='hash'),
    )

    @property
    def elapsed(self):
        """Returns the elapsed time with seconds precision."""
        t = self.end_time - self.start_time
        return timedelta(seconds=t.seconds)

    @property
    def url(self) -> urlutils.URL:
        """The URL where to GET this action."""
        return urlutils.URL(url_for_resource(Action, item_id=self.id))

    @property
    def certificate(self) -> Optional[urlutils.URL]:
        return None

    # noinspection PyMethodParameters
    @declared_attr
    def __mapper_args__(cls):
        """Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Action':
            args[POLYMORPHIC_ON] = cls.type
        # noinspection PyUnresolvedReferences
        if JoinedTableMixin in cls.mro():
            args[INHERIT_COND] = cls.id == Action.id
        return args

    @property
    def date_str(self):
        return '{:%c}'.format(self.end_time)

    def __init__(self, **kwargs) -> None:
        # sortedset forces us to do this before calling our parent init
        self.end_time = kwargs.get('end_time', None)
        if not self.end_time:
            # Set default for end_time, make it the same of created
            kwargs['created'] = self.end_time = datetime.now(timezone.utc)
        super().__init__(**kwargs)

    def __lt__(self, other):
        return self.end_time.replace(tzinfo=tzutc()) < other.end_time.replace(
            tzinfo=tzutc()
        )

    def __str__(self) -> str:
        return '{}'.format(self.severity)

    def __repr__(self):
        return '<{0.t} {0.id} {0.severity}>'.format(self)


class ActionComponent(db.Model):
    device_id = Column(BigInteger, ForeignKey(Component.id), primary_key=True)
    action_id = Column(UUID(as_uuid=True), ForeignKey(Action.id), primary_key=True)


class JoinedWithOneDeviceMixin:
    # noinspection PyMethodParameters
    @declared_attr
    def id(cls):
        return Column(
            UUID(as_uuid=True), ForeignKey(ActionWithOneDevice.id), primary_key=True
        )


class ActionWithOneDevice(JoinedTableMixin, Action):
    device_id = Column(BigInteger, ForeignKey(Device.id), nullable=False)
    device = relationship(
        Device,
        backref=backref(
            'actions_one', lazy=True, cascade=CASCADE_OWN, **_sorted_actions
        ),
        primaryjoin=Device.id == device_id,
    )

    __table_args__ = (
        db.Index('action_one_device_id_index', device_id, postgresql_using='hash'),
    )

    def __repr__(self) -> str:
        return '<{0.t} {0.id} {0.severity} device={0.device!r}>'.format(self)

    @declared_attr
    def __mapper_args__(cls):
        """Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'ActionWithOneDevice':
            args[POLYMORPHIC_ON] = cls.type
        return args


class ActionWithMultipleDevices(Action):
    devices = relationship(
        Device,
        backref=backref('actions_multiple', lazy=True, **_sorted_actions),
        secondary=lambda: ActionDevice.__table__,
        order_by=lambda: Device.id,
        collection_class=OrderedSet,
    )

    def __repr__(self) -> str:
        return '<{0.t} {0.id} {0.severity} devices={0.devices!r}>'.format(self)


class ActionDevice(db.Model):
    device_id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    action_id = Column(
        UUID(as_uuid=True), ForeignKey(ActionWithMultipleDevices.id), primary_key=True
    )
    device = relationship(
        Device,
        backref=backref('actions_device', lazy=True),
        primaryjoin=Device.id == device_id,
    )
    action = relationship(
        Action,
        backref=backref('actions_device', lazy=True),
        primaryjoin=Action.id == action_id,
    )
    created = db.Column(
        db.TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
        server_default=db.text('CURRENT_TIMESTAMP'),
    )
    created.comment = """When Devicehub created this."""
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    # todo compute the org
    author = relationship(
        User,
        backref=backref('authored_actions_device', lazy=True, collection_class=set),
        primaryjoin=author_id == User.id,
    )

    def __init__(self, **kwargs) -> None:
        self.created = kwargs.get('created', datetime.now(timezone.utc))
        super().__init__(**kwargs)


class ActionWithMultipleTradeDocuments(ActionWithMultipleDevices):
    documents = relationship(
        TradeDocument,
        backref=backref('actions_docs', lazy=True, **_sorted_actions),
        secondary=lambda: ActionTradeDocument.__table__,
        order_by=lambda: TradeDocument.id,
        collection_class=OrderedSet,
    )


class ActionTradeDocument(db.Model):
    document_id = Column(BigInteger, ForeignKey(TradeDocument.id), primary_key=True)
    action_id = Column(
        UUID(as_uuid=True),
        ForeignKey(ActionWithMultipleTradeDocuments.id),
        primary_key=True,
    )


class Add(ActionWithOneDevice):
    """The act of adding components to a device.

    It is usually used internally from a :class:`.Snapshot`, for
    example, when adding a secondary data storage to a computer.
    """


class Remove(ActionWithOneDevice):
    """The act of removing components from a device.

    It is usually used internally from a :class:`.Snapshot`, for
    example, when removing a component from a broken computer.
    """


class Allocate(JoinedTableMixin, ActionWithMultipleDevices):
    """The act of allocate one list of devices to one person"""

    final_user_code = Column(CIText(), default='', nullable=True)
    final_user_code.comment = """This is a internal code for mainteing the secrets of the
        personal datas of the new holder"""
    transaction = Column(CIText(), default='', nullable=True)
    transaction.comment = (
        "The code used from the owner for relation with external tool."
    )
    end_users = Column(Numeric(precision=4), check_range('end_users', 0), nullable=True)


class Deallocate(JoinedTableMixin, ActionWithMultipleDevices):
    """The act of deallocate one list of devices to one person of the system or not"""

    transaction = Column(CIText(), default='', nullable=True)
    transaction.comment = (
        "The code used from the owner for relation with external tool."
    )


class EraseBasic(JoinedWithOneDeviceMixin, ActionWithOneDevice):
    """An erasure attempt to a ``DataStorage``. The action contains
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
        # todo will this url_for_resource work for other resources?
        return urlutils.URL(url_for_resource('Document', item_id=self.id))

    def get_phid(self):
        """This method is used for get the phid of the computer when the action
        was created. Usefull for get the phid of the computer were a hdd was
        Ereased.
        """
        if self.snapshot:
            return self.snapshot.device.phid()
        if self.parent:
            return self.parent.phid()
        return ''

    def connect_api(self):
        if 'dpp' not in app.blueprints.keys() or not self.snapshot:
            return

        if not session.get('token_dlt'):
            return

        token_dlt = session.get('token_dlt')
        api_dlt = app.config.get('API_DLT')
        if not token_dlt or not api_dlt:
            return

        return API(api_dlt, token_dlt, "ethereum")

    def register_proof(self):
        """This method is used for register a proof of erasure en dlt."""
        from ereuse_devicehub.modules.dpp.models import PROOF_ENUM, ALGORITHM

        deviceCHID = self.device.chid
        docHash = self.snapshot.phid_dpp
        docHashAlgorithm = ALGORITHM
        proof_type = PROOF_ENUM['Erase']
        dh_instance = app.config.get('ID_FEDERATED', 'dh1')

        api = self.connect_api()
        if not api:
            return

        result = api.generate_proof(
            deviceCHID,
            docHashAlgorithm,
            docHash,
            proof_type,
            dh_instance,
        )

        self.register_erase_proof(result)

    def register_erase_proof(self, result):
        from ereuse_devicehub.modules.dpp.models import PROOF_ENUM, Proof
        from ereuse_devicehub.resources.enums import StatusCode

        if result['Status'] == StatusCode.Success.value:
            timestamp = result.get('Data', {}).get('data', {}).get('timestamp')
            if not timestamp:
                return

            d = {
                "type": PROOF_ENUM['Erase'],
                "device": self.device,
                "action": self.snapshot,
                "documentId": self.snapshot.id,
                "timestamp": timestamp,
                "issuer_id": g.user.id,
                "documentSignature": self.snapshot.phid_dpp,
                "normalizeDoc": self.snapshot.json_hw,
            }
            proof = Proof(**d)
            db.session.add(proof)

    def get_public_name(self):
        return "Basic"

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
                standard = ','.join([x.value for x in self.standards])
                std = 'with standards {}'.format(standard)
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

    def get_public_name(self):
        steps_random = 0
        steps_zeros = 0
        for s in self.steps:
            if s.type == 'StepRandom':
                steps_random += 1
            if s.type == 'StepZero':
                steps_zeros += 1

        if steps_zeros == 0 and steps_random == 1:
            return "Basic"
        if steps_zeros == 1 and steps_random == 1:
            return "Baseline"
        if steps_zeros == 1 and steps_random == 2:
            return "Enhanced"

        return "Custom"


class ErasePhysical(EraseBasic):
    """The act of physically destroying a data storage unit."""

    method = Column(DBEnum(PhysicalErasureMethod))

    def get_public_name(self):
        return "Physical"


class EraseDataWipe(EraseBasic):
    """The device has been selected for insert one proof of erease disk."""

    id = Column(UUID(as_uuid=True), ForeignKey(EraseBasic.id), primary_key=True)
    document_comment = """The user that gets the device due this deal."""
    document_id = db.Column(
        BigInteger, db.ForeignKey('data_wipe_document.id'), nullable=False
    )
    document = db.relationship(
        'DataWipeDocument',
        backref=backref('erase_actions', lazy=True, cascade=CASCADE_OWN),
        primaryjoin='EraseDataWipe.document_id == DataWipeDocument.id',
    )

    def get_public_name(self):
        return "EraseDataWipe"

    def __format__(self, format_spec: str) -> str:
        v = ''
        if 't' in format_spec:
            v += '{} {}. '.format(self.type, self.severity.get_public_name())
        if 's' in format_spec:
            if not self.document:
                v += 'On {}'.format(self.date_str)
                return v
            software = self.document.software or ''
            url = self.document.url or ''
            v += 'Software: {}, {}. '.format(software, url)
            v += 'On {}'.format(self.date_str)
        return v

    @property
    def date_str(self):
        day = self.created
        if self.document:
            day = self.document.date or self.end_time or self.created
        return '{:%c}'.format(day)


class Step(db.Model):
    erasure_id = Column(
        UUID(as_uuid=True),
        ForeignKey(EraseBasic.id, ondelete='CASCADE'),
        primary_key=True,
    )
    type = Column(Unicode(STR_SM_SIZE), nullable=False)
    num = Column(SmallInteger, primary_key=True)
    severity = Column(
        ereuse_devicehub.teal.db.IntEnum(Severity),
        default=Severity.Info,
        nullable=False,
    )
    start_time = Column(db.TIMESTAMP(timezone=True), nullable=False)
    start_time.comment = Action.start_time.comment
    end_time = Column(
        db.TIMESTAMP(timezone=True),
        CheckConstraint('end_time > start_time'),
        nullable=False,
    )
    end_time.comment = Action.end_time.comment

    erasure = relationship(
        EraseBasic,
        backref=backref(
            'steps',
            cascade=CASCADE_OWN,
            order_by=num,
            collection_class=ordering_list('num'),
        ),
    )

    @property
    def elapsed(self):
        """Returns the elapsed time with seconds precision."""
        t = self.end_time - self.start_time
        return timedelta(seconds=t.seconds)

    # noinspection PyMethodParameters
    @declared_attr
    def __mapper_args__(cls):
        """Defines inheritance.

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


class Snapshot(JoinedWithOneDeviceMixin, ActionWithOneDevice):
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
    and then performs more actions (like testings, benchmarking...).

    There are two ways of sending this information. In an async way,
    this is, submitting actions as soon as Workbench performs then, or
    submitting only one Snapshot action with all the other actions embedded.

    **Asynced**

    The use case, which is represented in the ``test_workbench_phases``,
    is as follows:

    1. In **T1**, WorkbenchServer (as the middleware from Workbench and
       Devicehub) submits:

       - A ``Snapshot`` action with the required information to **synchronize**
         and **rate** the device. This is:

           - Identification information about the device and components
             (S/N, model, physical characteristics...)
           - ``Tags`` in a ``tags`` property in the ``device``.
           - ``Rate`` in an ``actions`` property in the ``device``.
           - ``Benchmarks`` in an ``actions`` property in each ``component``
             or ``device``.
           - ``TestDataStorage`` as in ``Benchmarks``.
       - An ordered set of **expected actions**, defining which are the next
         actions that Workbench will perform to the device in ideal
         conditions (device doesn't fail, no Internet drop...).

       Devicehub **syncs** the device with the database and perform the
       ``Benchmark``, the ``TestDataStorage``, and finally the ``Rate``.
       This leaves the Snapshot **open** to wait for the next actions
       to come.
    2. Assuming that we expect all actions, in **T2**, WorkbenchServer
       submits a ``StressTest`` with a ``snapshot`` field containing the
       ID of the Snapshot in 1, and Devicehub links the action with such
       ``Snapshot``.
    3. In **T3**, WorkbenchServer submits the ``Erase`` with the ``Snapshot``
       and ``component`` IDs from 1, linking it to them. It repeats
       this for all the erased data storage devices; **T3+Tn** being
       *n* the erased data storage devices.
    4. WorkbenchServer does like in 3. but for the action ``Install``,
       finishing in **T3+Tn+Tx**, being *x* the number of data storage
       devices with an OS installed into.
    5. In **T3+Tn+Tx**, when all *expected actions* have been performed,
       Devicehub **closes** the ``Snapshot`` from 1.

    **Synced**

    Optionally, Devicehub understands receiving a ``Snapshot`` with all
    the actions in an ``actions`` property inside each affected ``component``
    or ``device``.
    """

    uuid = Column(UUID(as_uuid=True), unique=True)
    version = Column(StrictVersionType(STR_SM_SIZE), nullable=False)
    software = Column(DBEnum(SnapshotSoftware), nullable=False)
    elapsed = Column(Interval)
    elapsed.comment = """For Snapshots made with Workbench, the total amount
    of time it took to complete.
    """
    sid = Column(CIText(), nullable=True)
    settings_version = Column(CIText(), nullable=True)
    is_server_erase = Column(Boolean(), nullable=True)
    json_wb = Column(CIText(), nullable=False)
    json_wb.comment = "original json of the workbench"
    json_hw = Column(CIText(), nullable=False)
    json_hw.comment = (
        "json with alphabetic ordered of the hardware than exist in json_wb"
    )
    phid_dpp = Column(CIText(), nullable=False)
    phid_dpp.comment = "hash of json_hw this with the chid if the device conform the DPP, (Digital PassPort)"

    def create_json_hw(self, json_wb):
        """
        Create a json with the hardware without actions of the original json, (json_wb).
        This json need have an alphabetic order.
        Next is necessary create a hash of this json and put it intu phid field.
        And last save in text the correct json_wb and json_hw in the respective fields
        """
        if not json_wb:
            return

        json_hw = {}
        json_wb = copy.copy(json_wb)

        if json_wb.get('device', {}).get('system_uuid'):
            system_uuid = str(json_wb['device']['system_uuid'])
            json_wb['device']['system_uuid'] = system_uuid

        for k, v in json_wb.items():
            if k == 'device':
                json_hw['device'] = copy.copy(v)
                json_hw['device'].pop('actions', None)
                json_hw['device'].pop('actions_one', None)
            if k == 'components':
                components = []
                for component in v:
                    c = component
                    c.pop('actions', None)
                    c.pop('actions_one', None)
                    components.append(c)
                # if 'manufacturer', 'model', 'serialNumber' key filter broken'
                # key_filter = itemgetter('type', 'manufacturer', 'model', 'serialNumber')
                key_filter = itemgetter('type')
                json_hw['components'] = sorted(components, key=key_filter)
        self.json_wb = json.dumps(json_wb)
        self.json_hw = json.dumps(json_hw)
        self.phid_dpp = hashlib.sha3_256(self.json_hw.encode('utf-8')).hexdigest()

    def get_last_lifetimes(self):
        """We get the lifetime and serial_number of the first disk"""
        hdds = []
        components = [c for c in self.components]
        components.sort(key=lambda x: x.created)
        for hd in components:
            data = {'serial_number': None, 'lifetime': 0}
            if not isinstance(hd, DataStorage):
                continue

            data['serial_number'] = hd.serial_number
            for act in hd.actions:
                if not act.type == "TestDataStorage":
                    continue
                if not act.lifetime:
                    continue
                data['lifetime'] = act.lifetime.total_seconds() / 3600
                break
            hdds.append(data)

        return hdds

    def get_new_device(self):
        if not self.device:
            return ''

        snapshots = []
        for s in self.device.actions:
            if s == self:
                break
            if s.type == self.type:
                snapshots.append(s)
        return snapshots and 'update' or 'new_device'

    def register_passport_dlt(self):
        if 'dpp' not in app.blueprints.keys() or not self.device.hid:
            return

        from ereuse_devicehub.modules.dpp.models import Dpp, ALGORITHM

        dpp = "{chid}:{phid}".format(chid=self.device.chid, phid=self.phid_dpp)
        if Dpp.query.filter_by(key=dpp).all():
            return

        if not session.get('token_dlt'):
            return

        token_dlt = session.get('token_dlt')
        api_dlt = app.config.get('API_DLT')
        dh_instance = app.config.get('ID_FEDERATED', 'dh1')
        if not token_dlt or not api_dlt:
            return

        api = API(api_dlt, token_dlt, "ethereum")
        docSig = self.phid_dpp
        
        cny_a = 1
        while cny_a:
            try:
                result = api.issue_passport(dpp, ALGORITHM, docSig, dh_instance)
                cny_a = 0
            except Exception as err:
                logger.error("ERROR API issue passport return: %s", err)
                time.sleep(5)

        if result['Status'] is not StatusCode.Success.value:
            return

        timestamp = result['Data'].get('data', {}).get('timestamp', time.time())
        docID = "{}".format(self.uuid or '')
        d_issue = {
            "device_id": self.device.id,
            "snapshot": self,
            "timestamp": timestamp,
            "issuer_id": g.user.id,
            "documentId": docID,
            "key": dpp,
        }
        dpp_issue = Dpp(**d_issue)
        db.session.add(dpp_issue)

    def __str__(self) -> str:
        return '{}. {} version {}.'.format(self.severity, self.software, self.version)


class Install(JoinedWithOneDeviceMixin, ActionWithOneDevice):
    """The action of installing an Operative System to a data
    storage unit.
    """

    elapsed = Column(Interval, nullable=False)
    address = Column(SmallInteger, check_range('address', 8, 256))


class SnapshotRequest(db.Model):
    id = Column(UUID(as_uuid=True), ForeignKey(Snapshot.id), primary_key=True)
    request = Column(JSON, nullable=False)
    snapshot = relationship(
        Snapshot,
        backref=backref('request', lazy=True, uselist=False, cascade=CASCADE_OWN),
    )


class Benchmark(JoinedWithOneDeviceMixin, ActionWithOneDevice):
    """The act of gauging the performance of a device."""

    elapsed = Column(Interval)

    @declared_attr
    def __mapper_args__(cls):
        """Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Benchmark':
            args[POLYMORPHIC_ON] = cls.type
        return args


class BenchmarkMixin:
    # noinspection PyMethodParameters
    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), ForeignKey(Test.id), primary_key=True)


class BenchmarkDataStorage(Benchmark):
    """Benchmarks the data storage unit reading and writing speeds."""

    id = Column(UUID(as_uuid=True), ForeignKey(Benchmark.id), primary_key=True)
    read_speed = Column(Float(decimal_return_scale=2), nullable=False)
    write_speed = Column(Float(decimal_return_scale=2), nullable=False)

    def __str__(self) -> str:
        return 'Read: {0:.2f} MB/s, write: {0:.2f} MB/s'.format(  # noqa: F523
            self.read_speed, self.write_speed
        )


class BenchmarkWithRate(Benchmark):
    """The act of benchmarking a device with a single rate."""

    id = Column(UUID(as_uuid=True), ForeignKey(Benchmark.id), primary_key=True)
    rate = Column(Float, nullable=False)

    def __str__(self) -> str:
        return '{0:.2f} points'.format(self.rate)


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

    pass


class BenchmarkRamSysbench(BenchmarkWithRate):
    """Benchmarks a RAM by using the ram benchmarking
    utility of `sysbench <https://github.com/akopytov/sysbench>`_.
    """

    pass


class BenchmarkGraphicCard(BenchmarkWithRate):
    pass


class Test(JoinedWithOneDeviceMixin, ActionWithOneDevice):
    """The act of documenting the functionality of a device, as
    for the R2 Standard (R2 Provision 6 pag.19).

    :attr:`.severity` in :class:`Action` defines a passing or failing
    test, and
    :attr:`ereuse_devicehub.resources.device.models.Device.working`
    in Device gets all tests with warnings or errors for a device.
    """

    @declared_attr
    def __mapper_args__(cls):
        """Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Test':
            args[POLYMORPHIC_ON] = cls.type
        return args


class TestMixin:
    # noinspection PyMethodParameters
    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), ForeignKey(Test.id), primary_key=True)


class MeasureBattery(TestMixin, Test):
    """A sample of the status of the battery.

    Ref in R2 Provision 6 pag.22 Example:
    Length of charge; Expected results: Minimum 40 minutes.

    Operative Systems keep a record of several aspects of a battery.
    This is a sample of those.

    Failing and warning conditions are as follows:

    * :attr:`Severity.Error`: whether the health are Dead, Overheat or OverVoltage.
    * :attr:`Severity.Warning`: whether the health are UnspecifiedValue or Cold.
    """

    size = db.Column(db.Integer, nullable=False)
    size.comment = """Maximum battery capacity, in mAh."""
    voltage = db.Column(db.Integer, nullable=False)
    voltage.comment = """The actual voltage of the battery, in mV."""
    cycle_count = db.Column(db.Integer)
    cycle_count.comment = """The number of full charges – discharges
    cycles.
    """
    health = db.Column(db.Enum(BatteryHealth))
    health.comment = """The health of the Battery.
    Only reported in Android.
    """


class TestDataStorage(TestMixin, Test):
    """The act of testing the data storage.

    Testing is done using the `S.M.A.R.T self test
    <https://en.wikipedia.org/wiki/S.M.A.R.T.#Self-tests>`_. Note
    that not all data storage units, specially some new PCIe ones, do not
    support SMART testing.

    The test takes to other SMART values indicators of the overall health
    of the data storage.

    Failing and warning conditions are as follows:

    * :attr:`Severity.Error`: whether the SMART test failed.
    * :attr:`Severity.Warning`: if there is a significant chance for
      the data storage to fail in the following year.
    """

    length = Column(DBEnum(TestDataStorageLength), nullable=False)  # todo from type
    status = Column(Unicode(), check_lower('status'), nullable=False)
    lifetime = Column(Interval)
    assessment = Column(Boolean)
    reallocated_sector_count = Column(BigInteger)
    power_cycle_count = Column(Integer)
    _reported_uncorrectable_errors = Column('reported_uncorrectable_errors', BigInteger)
    command_timeout = Column(BigInteger)
    current_pending_sector_count = Column(BigInteger)
    offline_uncorrectable = Column(BigInteger)
    remaining_lifetime_percentage = Column(SmallInteger)
    elapsed = Column(Interval, nullable=False)

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
            elif (
                self.current_pending_sector_count
                and self.current_pending_sector_count > 40
                or self.reallocated_sector_count
                and self.reallocated_sector_count > 10
            ):
                self.severity = Severity.Warning

    def __str__(self) -> str:
        t = inflection.humanize(self.status)
        if self.lifetime:
            t += ' with a lifetime of {:.1f} years.'.format(self.lifetime.days / 365)
        t += self.description
        return t

    @property
    def reported_uncorrectable_errors(self):
        return self._reported_uncorrectable_errors

    @property
    def power_on_hours(self):
        if not self.lifetime:
            return 0
        return int(self.lifetime.total_seconds() / 3600)

    @reported_uncorrectable_errors.setter
    def reported_uncorrectable_errors(self, value):
        # We assume that a huge number is not meaningful
        # So we keep it like this
        self._reported_uncorrectable_errors = min(value, db.PSQL_INT_MAX)


class StressTest(TestMixin, Test):
    """The act of stressing (putting to the maximum capacity)
    a device for an amount of minutes.

    Failing and warning conditions are as follows:

    * :attr:`Severity.Error`: whether failed StressTest.
    * :attr:`Severity.Warning`: if stress test are less than 5 minutes.
    """

    elapsed = Column(Interval, nullable=False)

    @validates('elapsed')
    def is_minute_and_bigger_than_1_minute(self, _, value: timedelta):
        seconds = value.total_seconds()
        assert not bool(seconds % 60)
        assert seconds >= 60
        return value

    def __str__(self) -> str:
        return '{}. Computing for {}'.format(self.severity, self.elapsed)


class TestAudio(TestMixin, Test):
    """The act of checking the audio aspects of the device.

    Failing and warning conditions are as follows:

    * :attr:`Severity.Error`: whether speaker or microphone variables fail.
    * :attr:`Severity.Warning`: .
    """

    _speaker = Column('speaker', Boolean)
    _speaker.comment = """Whether the speaker works as expected."""
    _microphone = Column('microphone', Boolean)
    _microphone.comment = """Whether the microphone works as expected."""

    @property
    def speaker(self):
        return self._speaker

    @speaker.setter
    def speaker(self, x):
        self._speaker = x
        self._check()

    @property
    def microphone(self):
        return self._microphone

    @microphone.setter
    def microphone(self, x):
        self._microphone = x
        self._check()

    def _check(self):
        """Sets ``severity`` to ``error`` if any of the variables fail."""
        if not self._speaker or not self._microphone:
            self.severity = Severity.Error


class TestConnectivity(TestMixin, Test):
    """The act of testing the connectivity of the device.

    A failing test means that at least one connection of the device
    is not working well. A comment should get into more detail.
    """


class TestCamera(TestMixin, Test):
    """Tests the working conditions of the camera of the device,
    specially when taking pictures or recording video.

    Failing and warning conditions are as follows:

    * :attr:`Severity.Error`: whether the camera cannot turn on or
      has significant visual problems.
    * :attr:`Severity.Warning`: whether there are small visual problems
      with the camera (like dust) that it still allows it to be used.
    """


class TestKeyboard(TestMixin, Test):
    """Whether the keyboard works correctly.

    Failing and warning conditions are as follows:

    * :attr:`Severity.Error`: if at least one key does not produce
      a character on screen. This follows R2 Provision 6 pag.22.
    """


class TestTrackpad(TestMixin, Test):
    """Whether the trackpad works correctly.

     Failing and warning conditions are as follows:

    * :attr:`Severity.Error`: if the cursor does not move on screen.
      This follows R2 Provision 6 pag.22.
    """


class TestDisplayHinge(TestMixin, Test):
    """Whether display hinge works correctly.

    Failing and warning conditions are as follows:

    * :attr:`Severity.Error`: whether the laptop does not stay open
      or closed at desired angles. From R2 Provision 6 pag.22.
    """


class TestPowerAdapter(TestMixin, Test):
    """Whether power adapter charge battery device without problems.

    Failing and warning conditions are as follows:

    * :attr:`Severity.Error`: if the laptop does not charge battery.
      This follows R2 Provision 6 pag.22.
    """


class TestBios(TestMixin, Test):
    """Tests the working condition and grades the usability of the BIOS.

    Failing and warning conditions are as follows:

    * :attr:`Severity.Error`: whether Bios beeps or access range is D or E.
    * :attr:`Severity.Warning`: whether access range is B or C.
    """

    beeps_power_on = Column(Boolean)
    beeps_power_on.comment = """Whether there are no beeps or error
    codes when booting up.

    Reference: R2 provision 6 page 23.
    """
    access_range = Column(DBEnum(BiosAccessRange))
    access_range.comment = """Difficulty to modify the boot menu.

    This is used as an usability measure for accessing and modifying
    a bios, specially as something as important as modifying the boot
    menu.
    """


class VisualTest(TestMixin, Test):
    """The act of visually inspecting the appearance and functionality
    of the device.

    Reference R2 provision 6 Templates Ready for Resale Checklist (Desktop)
    https://sustainableelectronics.org/sites/default/files/6.c.2%20Desktop%20R2-Ready%20for%20Resale%20Checklist.docx
    Physical condition grade.

    Failing and warning conditions are as follows:

    * :attr:`Severity.Error`: whether appearance range is less than B or
                                functionality range is less than B.
    * :attr:`Severity.Warning`: whether appearance range is B or A and
                                functionality range is B.
    * :attr:`Severity.Info`: whether appearance range is B or A and
                                functionality range is A.
    """

    appearance_range = Column(DBEnum(AppearanceRange), nullable=True)
    appearance_range.comment = AppearanceRange.__doc__
    functionality_range = Column(DBEnum(FunctionalityRange), nullable=True)
    functionality_range.comment = FunctionalityRange.__doc__
    labelling = Column(Boolean)
    labelling.comment = """Whether there are tags to be removed."""

    def __str__(self) -> str:
        return super().__str__() + '. Appearance {} and functionality {}'.format(
            self.appearance_range, self.functionality_range
        )


class Rate(JoinedWithOneDeviceMixin, ActionWithOneDevice):
    """The act of computing a rate based on different categories:

    * Functionality (F). Tests, the act of testing usage condition of a device
    * Appearance (A). Visual evaluation, surface deterioration.
    * Performance (Q). Components characteristics and components benchmarks.
    """

    N = 2
    """The number of significant digits for rates.
    Values are rounded and stored to it.
    """

    _rating = Column(
        'rating', Float(decimal_return_scale=N), check_range('rating', *R_POSITIVE)
    )
    _rating.comment = """The rating for the content."""
    version = Column(StrictVersionType)
    version.comment = """The version of the software."""
    _appearance = Column(
        'appearance',
        Float(decimal_return_scale=N),
        check_range('appearance', *R_NEGATIVE),
    )
    _appearance.comment = """Subjective value representing aesthetic aspects."""
    _functionality = Column(
        'functionality',
        Float(decimal_return_scale=N),
        check_range('functionality', *R_NEGATIVE),
    )
    _functionality.comment = """Subjective value representing usage aspects."""

    @property
    def rating(self):
        return self._rating

    @rating.setter
    def rating(self, x):
        self._rating = round(max(x, 0), self.N)

    @property
    def appearance(self):
        return self._appearance

    @appearance.setter
    def appearance(self, x):
        self._appearance = round(x, self.N)

    @property
    def functionality(self):
        return self._functionality

    @functionality.setter
    def functionality(self, x):
        self._functionality = round(x, self.N)

    @property
    def rating_range(self) -> RatingRange:
        """"""
        return RatingRange.from_score(self.rating) if self.rating else None

    @declared_attr
    def __mapper_args__(cls):
        """Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Rate':
            args[POLYMORPHIC_ON] = cls.type
        return args

    def __str__(self) -> str:
        if self.version:
            return '{} (v.{})'.format(self.rating_range, self.version)

        return '{}'.format(self.rating_range)

    @classmethod
    def compute(cls, device) -> 'RateComputer':
        raise NotImplementedError()


class RateMixin:
    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), ForeignKey(Rate.id), primary_key=True)


class RateComputer(RateMixin, Rate):
    """The act of rating a computer type devices.
    It's the starting point for calculating the rate.
    Algorithm explained in v1.0 file.
    """

    _processor = Column(
        'processor',
        Float(decimal_return_scale=Rate.N),
        check_range('processor', *R_POSITIVE),
    )
    _processor.comment = """The rate of the Processor."""
    _ram = Column(
        'ram', Float(decimal_return_scale=Rate.N), check_range('ram', *R_POSITIVE)
    )
    _ram.comment = """The rate of the RAM."""
    _data_storage = Column(
        'data_storage',
        Float(decimal_return_scale=Rate.N),
        check_range('data_storage', *R_POSITIVE),
    )
    _data_storage.comment = """'Data storage rate, like HHD, SSD.'"""
    _graphic_card = Column(
        'graphic_card',
        Float(decimal_return_scale=Rate.N),
        check_range('graphic_card', *R_POSITIVE),
    )
    _graphic_card.comment = 'Graphic card rate.'

    @property
    def processor(self):
        return self._processor

    @processor.setter
    def processor(self, x):
        self._processor = round(x, self.N)

    @property
    def ram(self):
        return self._ram

    @ram.setter
    def ram(self, x):
        self._ram = round(x, self.N)

    @property
    def data_storage(self):
        return self._data_storage

    @data_storage.setter
    def data_storage(self, x):
        self._data_storage = round(x, self.N)

    @property
    def graphic_card(self):
        return self._graphic_card

    @graphic_card.setter
    def graphic_card(self, x):
        self._graphic_card = round(x, self.N)

    @property
    def data_storage_range(self):
        return RatingRange.from_score(self.data_storage) if self.data_storage else None

    @property
    def ram_range(self):
        return RatingRange.from_score(self.ram) if self.ram else None

    @property
    def processor_range(self):
        return RatingRange.from_score(self.processor) if self.processor else None

    @property
    def graphic_card_range(self):
        return RatingRange.from_score(self.graphic_card) if self.graphic_card else None

    @classmethod
    def compute(cls, device):
        """The act of compute general computer rate."""
        from ereuse_devicehub.resources.action.rate.v1_0 import rate_algorithm

        rate = rate_algorithm.compute(device)
        price = None
        with suppress(
            InvalidRangeForPrice
        ):  # We will have exception if range == VERY_LOW
            price = EreusePrice(rate)
        return rate, price


class Price(JoinedWithOneDeviceMixin, ActionWithOneDevice):
    # TODO rewrite  Class comment change AggregateRate..
    """The act of setting a trading price for the device.

    This does not imply that the device is ultimately traded for that
    price. Use the :class:`.Sell` for that.

    Devicehub automatically computes a price from ``AggregateRating``
    actions. As in a **Rate**, price can have **software** and **version**,
    and there is an **official** price that is used to automatically
    compute the price from an ``AggregateRating``. Only the official price
    is computed from an ``AggregateRating``.
    """
    SCALE = 4
    ROUND = ROUND_HALF_EVEN
    currency = Column(DBEnum(Currency), nullable=False)
    currency.comment = """The currency of this price as for ISO 4217."""
    price = Column(
        Numeric(precision=19, scale=SCALE), check_range('price', 0), nullable=False
    )
    price.comment = """The value."""
    software = Column(DBEnum(PriceSoftware))
    software.comment = """The software used to compute this price,
    if the price was computed automatically. This field is None
    if the price has been manually set.
    """
    version = Column(StrictVersionType)
    version.comment = """The version of the software, or None."""
    rating_id = Column(UUID(as_uuid=True), ForeignKey(Rate.id))
    rating_id.comment = """The Rate used to auto-compute
    this price, if it has not been set manually.
    """
    rating = relationship(
        Rate,
        backref=backref('price', lazy=True, cascade=CASCADE_OWN, uselist=False),
        primaryjoin=Rate.id == rating_id,
    )

    def __init__(self, *args, **kwargs) -> None:
        if 'price' in kwargs:
            assert isinstance(kwargs['price'], Decimal), 'Price must be a Decimal'
        super().__init__(
            currency=kwargs.pop('currency', app.config['PRICE_CURRENCY']),
            *args,
            **kwargs,
        )

    @classmethod
    def to_price(cls, value: Union[Decimal, float], rounding=ROUND) -> Decimal:
        """Returns a Decimal value with the correct scale for Price.price."""
        if isinstance(value, (float, int)):
            value = Decimal(value)
        # equation from marshmallow.fields.Decimal
        return value.quantize(Decimal((0, (1,), -cls.SCALE)), rounding=rounding)

    @declared_attr
    def __mapper_args__(cls):
        """Defines inheritance.

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

    MULTIPLIER = {Computer: 20, Desktop: 20, Laptop: 30, Server: 40}

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
                    WARRANTY2: (0.47425, 0.275875, 0.599875),
                },
                RatingRange.MEDIUM: {
                    STANDARD: (0.385, 0.2558333333, 0.3591666667),
                    WARRANTY2: (0.539, 0.3581666667, 0.5028333333),
                },
                RatingRange.LOW: {
                    STANDARD: (0.5025, 0.30875, 0.18875),
                },
            },
            Laptop: {
                RatingRange.HIGH: {
                    STANDARD: (0.3469230769, 0.195, 0.4580769231),
                    WARRANTY2: (0.4522307692, 0.2632307692, 0.6345384615),
                },
                RatingRange.MEDIUM: {
                    STANDARD: (0.382, 0.1735, 0.4445),
                    WARRANTY2: (0.5108, 0.2429, 0.6463),
                },
                RatingRange.LOW: {
                    STANDARD: (0.4528571429, 0.2264285714, 0.3207142857),
                },
            },
        }
        SCHEMA[Server] = SCHEMA[Computer] = SCHEMA[Desktop]

        def __init__(self, device, rating_range, role, price: Decimal) -> None:
            cls = device.__class__ if device.__class__ != Server else Desktop
            rate = self.SCHEMA[cls][rating_range]
            self.standard = EreusePrice.Type(rate[self.STANDARD][role], price)
            if self.WARRANTY2 in rate:
                self.warranty2 = EreusePrice.Type(rate[self.WARRANTY2][role], price)

    def __init__(self, rating: RateComputer, **kwargs) -> None:
        if not rating.rating_range or rating.rating_range == RatingRange.VERY_LOW:
            raise InvalidRangeForPrice()
        # We pass ROUND_UP strategy so price is always greater than what refurbisher... amounts
        price = self.to_price(
            rating.rating * self.MULTIPLIER[rating.device.__class__], ROUND_UP
        )
        super().__init__(
            rating=rating,
            device=rating.device,
            price=price,
            software=kwargs.pop('software', app.config['PRICE_SOFTWARE']),
            version=kwargs.pop('version', app.config['PRICE_VERSION']),
            **kwargs,
        )
        self._compute()

    @orm.reconstructor
    def _compute(self):
        """Calculates eReuse.org prices when initializing the instance
        from the price and other properties.
        """
        self.refurbisher = self._service(self.Service.REFURBISHER)
        self.retailer = self._service(self.Service.RETAILER)
        self.platform = self._service(self.Service.PLATFORM)
        if hasattr(self.refurbisher, 'warranty2'):
            self.warranty2 = round(
                self.refurbisher.warranty2.amount
                + self.retailer.warranty2.amount
                + self.platform.warranty2.amount,
                2,
            )

    def _service(self, role):
        return self.Service(self.device, self.rating.rating_range, role, self.price)


class ToRepair(ActionWithMultipleDevices):
    """Select a device to be repaired."""


class Repair(ActionWithMultipleDevices):
    """Repair is the act of performing reparations.

    If a repair without an error is performed,
    it represents that the reparation has been successful.
    """


class Ready(ActionWithMultipleDevices):
    """The device is ready to be used.

    This involves greater preparation from the ``Prepare`` action,
    and users should only use a device after this action is performed.

    Users usually require devices with this action before shipping them
    to costumers.
    """


class EWaste(ActionWithMultipleDevices):
    """The device is declared as e-waste, this device is not allow use more.

    Any people can declared as e-waste one device.
    """

    def register_proof(self, doc):
        """This method is used for register a proof of erasure en dlt."""

        if 'dpp' not in app.blueprints.keys():
            return

        if not session.get('token_dlt'):
            return

        if not doc:
            return

        self.doc = doc
        token_dlt = session.get('token_dlt')
        api_dlt = app.config.get('API_DLT')
        dh_instance = app.config.get('ID_FEDERATED', 'dh1')
        if not token_dlt or not api_dlt:
            return

        api = API(api_dlt, token_dlt, "ethereum")

        from ereuse_devicehub.modules.dpp.models import (
            PROOF_ENUM,
            Proof,
            ALGORITHM
        )
        from ereuse_devicehub.resources.enums import StatusCode

        for device in self.devices:
            deviceCHID = device.chid
            docHash = self.generateDocSig()
            docHashAlgorithm = ALGORITHM
            proof_type = PROOF_ENUM['EWaste']
            result = api.generate_proof(
                deviceCHID,
                docHashAlgorithm,
                docHash,
                proof_type,
                dh_instance,
            )

            if result['Status'] == StatusCode.Success.value:
                timestamp = result.get('Data', {}).get('data', {}).get('timestamp')

                if not timestamp:
                    return

                d = {
                    "type": PROOF_ENUM['EWaste'],
                    "device": device,
                    "action": self,
                    "documentId": self.id,
                    "timestamp": timestamp,
                    "issuer_id": g.user.id,
                    "documentSignature": docHash,
                    "normalizeDoc": self.doc,
                }
                proof = Proof(**d)
                db.session.add(proof)

    def generateDocSig(self):
        if not self.doc:
            return
        return hashlib.sha3_256(self.doc.encode('utf-8')).hexdigest()


class ToPrepare(ActionWithMultipleDevices):
    """The device has been selected for preparation.

    See Prepare for more info.

    Usually **ToPrepare** is the next action done after registering the
    device.
    """

    pass


class DataWipe(JoinedTableMixin, ActionWithMultipleDevices):
    # class DataWipe(JoinedWithOneDeviceMixin, ActionWithOneDevice):
    """The device has been selected for insert one proof of erease disk."""

    document_comment = """The user that gets the device due this deal."""
    document_id = db.Column(
        BigInteger, db.ForeignKey('data_wipe_document.id'), nullable=False
    )
    document = db.relationship(
        'DataWipeDocument',
        backref=backref('actions', lazy=True, cascade=CASCADE_OWN),
        primaryjoin='DataWipe.document_id == DataWipeDocument.id',
    )


class ActionStatus(JoinedTableMixin, ActionWithMultipleTradeDocuments):
    """This is a meta-action than mark the status of the devices"""

    rol_user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    rol_user = db.relationship(User, primaryjoin=rol_user_id == User.id)
    rol_user_comment = """The user that ."""
    trade_id = db.Column(UUID(as_uuid=True), db.ForeignKey('trade.id'), nullable=True)
    trade = db.relationship(
        'Trade',
        backref=backref(
            'status_changes',
            uselist=True,
            lazy=True,
            order_by=lambda: Action.end_time,
            collection_class=list,
        ),
        primaryjoin='ActionStatus.trade_id == Trade.id',
    )


class Recycling(ActionStatus):
    """This action mark devices as recycling"""


class Use(ActionStatus):
    """This action mark one devices or container as use"""


class Refurbish(ActionStatus):
    """This action mark one devices or container as refurbish"""


class Management(ActionStatus):
    """This action mark one devices or container as management"""


class Prepare(ActionWithMultipleDevices):
    """Work has been performed to the device to a defined point of
    acceptance.

    Users using this action have to agree what is this point
    of acceptance; for some is when the device just works, for others
    when some testing has been performed.
    """


class Live(JoinedWithOneDeviceMixin, ActionWithOneDevice):
    """A keep-alive from a device connected to the Internet with
    information about its state (in the form of a ``Snapshot`` action)
    and usage statistics.
    """

    serial_number = Column(Unicode(), check_lower('serial_number'))
    serial_number.comment = """The serial number of the Hard Disk in lower case."""
    usage_time_hdd = Column(Interval, nullable=True)
    snapshot_uuid = Column(UUID(as_uuid=True))
    software = Column(DBEnum(SnapshotSoftware), nullable=False)
    software_version = Column(StrictVersionType(STR_SM_SIZE), nullable=False)
    licence_version = Column(StrictVersionType(STR_SM_SIZE), nullable=False)

    @property
    def final_user_code(self):
        """show the final_user_code of the last action Allocate."""
        actions = self.device.actions
        actions.sort(key=lambda x: x.created)
        for e in reversed(actions):
            if isinstance(e, Allocate) and e.created < self.created:
                return e.final_user_code
        return ''

    @property
    def usage_time_allocate(self):
        """Show how many hours is used one device from the last check"""
        self.sort_actions()
        if self.usage_time_hdd is None:
            return self.last_usage_time_allocate()

        delta_zero = timedelta(0)
        diff_time = self.diff_time()
        if diff_time is None:
            return delta_zero

        if diff_time < delta_zero:
            return delta_zero
        return diff_time

    def sort_actions(self):
        self.actions = copy.copy(self.device.actions)
        self.actions.sort(key=lambda x: x.created)
        self.actions.reverse()

    def last_usage_time_allocate(self):
        """If we don't have self.usage_time_hdd then we need search the last
        action Live with usage_time_allocate valid"""
        for e in self.actions:
            if isinstance(e, Live) and e.created < self.created:
                if not e.usage_time_allocate:
                    continue
                return e.usage_time_allocate
        return timedelta(0)

    def get_last_snapshot_lifetime(self):
        for e in self.actions:
            if e.created > self.created:
                continue

            if isinstance(e, Snapshot):
                last_time = self.get_last_lifetime(e)
                if not last_time:
                    continue
                return last_time

    def diff_time(self):
        for e in self.actions:
            if e.created > self.created:
                continue

            if isinstance(e, Snapshot):
                last_time = self.get_last_lifetime(e)
                if not last_time:
                    continue
                return self.usage_time_hdd - last_time

            if isinstance(e, Live):
                if e.snapshot_uuid == self.snapshot_uuid:
                    continue

                if not e.usage_time_hdd:
                    continue
                return self.usage_time_hdd - e.usage_time_hdd
        return None

    def get_last_lifetime(self, snapshot):
        for a in snapshot.actions:
            if (
                a.type == 'TestDataStorage'
                and a.device.serial_number == self.serial_number
            ):
                return a.lifetime
        return None


class Organize(JoinedTableMixin, ActionWithMultipleDevices):
    """The act of manipulating/administering/supervising/controlling
    one or more devices.
    """


class Reserve(Organize):
    """The act of reserving devices.

    After this action is performed, the user is the **reservee** of the
    devices. There can only be one non-cancelled reservation for
    a device, and a reservation can only have one reservee.
    """


class CancelReservation(Organize):
    """The act of cancelling a reservation."""


class ActionStatusDocuments(JoinedTableMixin, ActionWithMultipleTradeDocuments):
    """This is a meta-action that marks the state of the devices."""

    rol_user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    rol_user = db.relationship(User, primaryjoin=rol_user_id == User.id)
    rol_user_comment = """The user that ."""


class RecyclingDocument(ActionStatusDocuments):
    """This action mark one document or container as recycling"""


class ConfirmDocument(JoinedTableMixin, ActionWithMultipleTradeDocuments):
    """Users confirm the one action trade this confirmation it's link to trade
    and the document that confirm
    """

    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    user = db.relationship(User, primaryjoin=user_id == User.id)
    user_comment = """The user that accept the offer."""
    action_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('action.id'), nullable=False
    )
    action = db.relationship(
        'Action',
        backref=backref(
            'acceptances_document',
            uselist=True,
            lazy=True,
            order_by=lambda: Action.end_time,
            collection_class=list,
        ),
        primaryjoin='ConfirmDocument.action_id == Action.id',
    )

    def __repr__(self) -> str:
        if self.action.t in ['Trade']:
            origin = 'To'
            if self.user == self.action.user_from:
                origin = 'From'
            return '<{0.t}app/views/inventory/ {0.id} accepted by {1}>'.format(
                self, origin
            )


class RevokeDocument(ConfirmDocument):
    pass


class ConfirmRevokeDocument(ConfirmDocument):
    pass


class Confirm(JoinedTableMixin, ActionWithMultipleDevices):
    """Users confirm the one action trade this confirmation it's link to trade
    and the devices that confirm
    """

    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    user = db.relationship(User, primaryjoin=user_id == User.id)
    user_comment = """The user that accept the offer."""
    action_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('action.id'), nullable=False
    )
    action = db.relationship(
        'Action',
        backref=backref(
            'acceptances',
            uselist=True,
            lazy=True,
            order_by=lambda: Action.end_time,
            collection_class=list,
        ),
        primaryjoin='Confirm.action_id == Action.id',
    )

    def __repr__(self) -> str:
        if self.action.t in ['Trade']:
            origin = 'To'
            if self.user == self.action.user_from:
                origin = 'From'
            return '<{0.t} {0.id} accepted by {1}>'.format(self, origin)


class Revoke(Confirm):
    """Users can revoke one confirmation of one action trade"""


# class ConfirmRevoke(Confirm):
#     """Users can confirm and accept one action revoke"""

#     def __repr__(self) -> str:
#         return '<{0.t} {0.id} accepted by {0.user}>'.format(self)


class Trade(JoinedTableMixin, ActionWithMultipleTradeDocuments):
    """Trade actions log the political exchange of devices between users.
    Every time a trade action is performed, the old user looses its
    political possession, for example ownership, in favor of another
    user.


    Performing trade actions changes the *Trading* state of the
    device —:class:`ereuse_devicehub.resources.device.states.Trading`.

    This class and its inheritors
    extend `Schema's Trade <http://schema.org/TradeAction>`_.
    """

    user_from_id = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), nullable=False)
    user_from = db.relationship(User, primaryjoin=user_from_id == User.id)
    user_from_comment = """The user that offers the device due this deal."""
    user_to_id = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), nullable=False)
    user_to = db.relationship(User, primaryjoin=user_to_id == User.id)
    user_to_comment = """The user that gets the device due this deal."""
    price = Column(Float(decimal_return_scale=2), nullable=True)
    currency = Column(DBEnum(Currency), nullable=False, default=Currency.EUR.name)
    currency.comment = """The currency of this price as for ISO 4217."""
    date = Column(db.TIMESTAMP(timezone=True))
    confirm = Column(Boolean, default=False, nullable=False)
    confirm.comment = (
        """If you need confirmation of the user, you need actevate this field"""
    )
    code = Column(CIText(), nullable=True)
    code.comment = (
        """If the user not exist, you need a code to be able to do the traceability"""
    )
    lot_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('lot.id', use_alter=True, name='lot_trade'),
        nullable=True,
    )
    lot = relationship(
        'Lot',
        backref=backref('trade', lazy=True, uselist=False, cascade=CASCADE_OWN),
        primaryjoin='Trade.lot_id == Lot.id',
    )

    def get_metrics(self):
        """
        This method get a list of values for calculate a metrics from a spreadsheet
        """
        metrics = []
        for doc in self.documents:
            m = TradeMetrics(document=doc, Trade=self)
            metrics.extend(m.get_metrics())
        return metrics

    def __repr__(self) -> str:
        return '<{0.t} {0.id} executed by {0.author}>'.format(self)


class InitTransfer(Trade):
    """The act of transfer ownership of devices between two agents"""


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


class TransferOwnershipBlockchain(Trade):
    """The act of change owenership of devices between two users (ethereum address)"""


class MakeAvailable(ActionWithMultipleDevices):
    """The act of setting willingness for trading."""

    pass


class MoveOnDocument(JoinedTableMixin, ActionWithMultipleTradeDocuments):
    """Action than certify one movement of some indescriptible material of
    one container to an other."""

    weight = db.Column(db.Float())
    weight.comment = """Weight than go to recycling"""
    container_from_id = db.Column(
        db.BigInteger, db.ForeignKey('trade_document.id'), nullable=False
    )
    container_from = db.relationship(
        'TradeDocument',
        backref=backref('containers_from', lazy=True, cascade=CASCADE_OWN),
        primaryjoin='MoveOnDocument.container_from_id == TradeDocument.id',
    )
    container_from_id.comment = (
        """This is the trade document used as container in a incoming lot"""
    )

    container_to_id = db.Column(
        db.BigInteger, db.ForeignKey('trade_document.id'), nullable=False
    )
    container_to = db.relationship(
        'TradeDocument',
        backref=backref('containers_to', lazy=True, cascade=CASCADE_OWN),
        primaryjoin='MoveOnDocument.container_to_id == TradeDocument.id',
    )
    container_to_id.comment = (
        """This is the trade document used as container in a outgoing lot"""
    )


class Delete(ActionWithMultipleDevices):
    # TODO in a new architecture we need rename this class to Deactivate

    """The act save in device who and why this devices was delete.
    We never delete one device, but we can deactivate."""
    pass


class Migrate(JoinedTableMixin, ActionWithMultipleDevices):
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

# The following listeners avoids setting values to actions that
# do not make sense. For example, EraseBasic to a graphic card.


@event.listens_for(TestDataStorage.device, Events.set.__name__, propagate=True)
@event.listens_for(Install.device, Events.set.__name__, propagate=True)
@event.listens_for(EraseBasic.device, Events.set.__name__, propagate=True)
def validate_device_is_data_storage(
    target: Action, value: DataStorage, old_value, initiator
):
    """Validates that the device for data-storage actions is effectively a data storage."""
    if value and not isinstance(value, DataStorage):
        raise TypeError(
            '{} must be a DataStorage but you passed {}'.format(initiator.impl, value)
        )


@event.listens_for(BenchmarkRamSysbench.device, Events.set.__name__, propagate=True)
def actions_not_for_components(target: Action, value: Device, old_value, initiator):
    """Validates actions that cannot be performed to components."""
    if isinstance(value, Component):
        raise TypeError(
            '{!r} cannot be performed to a component ({!r}).'.format(target, value)
        )


# The following listeners keep relationships with device <-> components synced with the action
# So, if you add or remove devices from actions these listeners will
# automatically add/remove the ``components`` and ``parent`` of such actions
# See the tests for examples


@event.listens_for(ActionWithOneDevice.device, Events.set.__name__, propagate=True)
def update_components_action_one(target: ActionWithOneDevice, device: Device, __, ___):
    """Syncs the :attr:`.Action.components` with the components in
    :attr:`ereuse_devicehub.resources.device.models.Computer.components`.
    """
    # For Add and Remove, ``components`` have different meanings
    # see Action.components for more info
    if not isinstance(target, (Add, Remove)):
        target.components.clear()
        if isinstance(device, Computer):
            target.components |= device.components
    elif isinstance(device, Computer):
        device.set_hid()


@event.listens_for(
    ActionWithMultipleDevices.devices, Events.init_collection.__name__, propagate=True
)
@event.listens_for(
    ActionWithMultipleDevices.devices, Events.bulk_replace.__name__, propagate=True
)
@event.listens_for(
    ActionWithMultipleDevices.devices, Events.append.__name__, propagate=True
)
def update_components_action_multiple(
    target: ActionWithMultipleDevices, value: Union[Set[Device], Device], _
):
    """Syncs the :attr:`.Action.components` with the components in
    :attr:`ereuse_devicehub.resources.device.models.Computer.components`.
    """
    target.components.clear()
    devices = value if isinstance(value, Iterable) else {value}
    for device in devices:
        if isinstance(device, Computer):
            target.components |= device.components


@event.listens_for(
    ActionWithMultipleDevices.devices, Events.remove.__name__, propagate=True
)
def remove_components_action_multiple(
    target: ActionWithMultipleDevices, device: Device, __
):
    """Syncs the :attr:`.Action.components` with the components in
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
    """Syncs the :attr:`Action.parent` with the parent of the device."""
    target.parent = None
    if isinstance(device, Component):
        target.parent = device.parent


class InvalidRangeForPrice(ValueError):
    pass
