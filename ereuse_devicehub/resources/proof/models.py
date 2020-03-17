"""This file contains all proofs related to actions

"""

from collections import Iterable
from datetime import datetime
from typing import Optional, Set, Union
from uuid import uuid4

from boltons import urlutils
from citext import CIText
from flask import current_app as app, g
from sortedcontainers import SortedSet
from sqlalchemy import BigInteger, Column, Enum as DBEnum, \
    ForeignKey, Integer, Unicode
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.util import OrderedSet
from teal.db import CASCADE_OWN, INHERIT_COND, POLYMORPHIC_ID, \
    POLYMORPHIC_ON, StrictVersionType, URL
from teal.marshmallow import ValidationError
from teal.resource import url_for_resource

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import Action, DisposeProduct, \
    EraseBasic, Rate, Trade
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.models import Thing


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
    ethereum_hash = Column(CIText(), default='', nullable=False)
    devices = relationship(Device,
                           backref=backref('proofs_multiple', lazy=True),
                           secondary=lambda: ProofDevice.__table__,
                           order_by=lambda: Device.id,
                           collection_class=OrderedSet)

    @property
    def url(self) -> urlutils.URL:
        """The URL where to GET this proof."""
        return urlutils.URL(url_for_resource(Proof, item_id=self.id))

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



class ProofDevice(db.Model):
    device_id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    proof_id = Column(UUID(as_uuid=True), ForeignKey(Proof.id),
                      primary_key=True)


class ProofTransfer(JoinedTableMixin, Proof):
    transfer_id = Column(UUID, ForeignKey(Trade.id), nullable=False)
    transfer = relationship(DisposeProduct,
                            backref=backref("proof_transfer",
                                            lazy=True,
                                            cascade=CASCADE_OWN),
                            uselist=False,
                            primaryjoin=DisposeProduct.id == transfer_id)


class ProofDataWipe(JoinedTableMixin, Proof):
    erasure_type = Column(CIText(), default='', nullable=False)
    date = Column(db.DateTime, nullable=False, default=datetime.utcnow)
    result = Column(db.Boolean, default=False, nullable=False)
    result.comment = """Identifies proof datawipe as a result."""
    erasure_id = Column(UUID(as_uuid=True), ForeignKey(EraseBasic.id), nullable=False)
    erasure = relationship(EraseBasic,
                           backref=backref('proof_datawipe',
                                           lazy=True,
                                           cascade=CASCADE_OWN),
                           primaryjoin=EraseBasic.id == erasure_id)


class ProofFunction(JoinedTableMixin, Proof):
    disk_usage = Column(db.Integer, default=0)
    rate_id = Column(UUID, ForeignKey(Rate.id), nullable=False)
    rate = relationship(Rate,
                       backref=backref('proof_function',
                                       lazy=True,
                                       cascade=CASCADE_OWN),
                        primaryjoin=Rate.id == rate_id)


class ProofReuse(JoinedTableMixin, Proof):
    price = Column(db.Integer)


class ProofRecycling(JoinedTableMixin, Proof):
    collection_point = Column(CIText(), default='', nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    contact = Column(CIText(), default='', nullable=False)
    ticket = Column(CIText(), default='', nullable=False)
    gps_location = Column(CIText(), default='', nullable=False)
