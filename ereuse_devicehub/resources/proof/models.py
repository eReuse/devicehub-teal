"""This file contains all proofs related to actions

"""

from collections import Iterable
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_UP
from typing import Optional, Set, Union
from uuid import uuid4

import inflection
import teal.db
from boltons import urlutils
from citext import CIText
from flask import current_app as app, g
from sortedcontainers import SortedSet
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Enum as DBEnum, \
    Float, ForeignKey, Integer, Interval, JSON, Numeric, SmallInteger, Unicode, event, orm
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.orm.events import AttributeEvents as Events
from sqlalchemy.util import OrderedSet
from teal.db import CASCADE_OWN, INHERIT_COND, IP, POLYMORPHIC_ID, \
    POLYMORPHIC_ON, StrictVersionType, URL, check_lower, check_range
from teal.enums import Country, Currency, Subdivision
from teal.marshmallow import ValidationError
from teal.resource import url_for_resource

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent.models import Agent
from ereuse_devicehub.resources.device.models import Component, Computer, DataStorage, Desktop, \
    Device, Laptop, Server
from ereuse_devicehub.resources.enums import AppearanceRange, BatteryHealth, BiosAccessRange, \
    ErasureStandards, FunctionalityRange, PhysicalErasureMethod, PriceSoftware, \
    R_NEGATIVE, R_POSITIVE, RatingRange, ReceiverRole, Severity, SnapshotSoftware, \
    TestDataStorageLength
from ereuse_devicehub.resources.models import STR_SM_SIZE, Thing
from ereuse_devicehub.resources.user.models import User


class JoinedTableMixin:
    # noinspection PyMethodParameters
    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), ForeignKey(Proof.id), primary_key=True)


class Proof(Thing):
    """Proof over an action.

    """
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    type = Column(Unicode, nullable=False)
    ethereum_hashes = Column(CIText(), default='', nullable=False)

    @property
    def url(self) -> urlutils.URL:
        """The URL where to GET this proof."""
        return urlutils.URL(url_for_resource(Proof, item_id=self.id))

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
        if cls.t == 'Proof':
            args[POLYMORPHIC_ON] = cls.type
        # noinspection PyUnresolvedReferences
        if JoinedTableMixin in cls.mro():
            args[INHERIT_COND] = cls.id == Proof.id
        return args

    def __init__(self, **kwargs) -> None:
        # sortedset forces us to do this before calling our parent init
        super().__init__(**kwargs)

    def __repr__(self):
        return '<{0.t} {0.id} >'.format(self)


class ProofTransfer(JoinedTableMixin, Proof):
    transfer_id = Column(BigInteger, ForeignKey(Action.id), nullable=False)
    transfer = relationship(DisposeProduct,
                            primaryjoin=DisposeProduct.id == transfer_id)


class ProofDataWipe(JoinedTableMixin, Proof):
    erasure_type = Column(CIText())
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    result = db.Column(db.Boolean, default=False, nullable=False)
    erasure_id = Column(BigInteger, ForeignKey(Device.id), nullable=False)
    erasure = relationship(EraseBasic,
                           backref=backref('proofs_datawipe',
                                           lazy=True,
                                           cascade=CASCADE_OWN),
                           primaryjoin=EraseBasic.id == erasure_id)


class ProofFunction(JoinedTableMixin, Proof):
    disk_usage = db.Column(db.Integer, default=0)
    rate_id = Column(BigInteger, ForeignKey(Rate.id), nullable=False)
    rate = relationship(Rate,
                        primaryjoin=Rate.id == rate_id)


class ProofReuse(JoinedTableMixin, Proof):
    price = db.Column(db.Integer, required=True)


class ProofRecycling(JoinedTableMixin, Proof):
    collection_point = Column(CIText())
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    contact = Column(CIText())
    ticket = Column(CIText())
    gps_location = Column(CIText())
