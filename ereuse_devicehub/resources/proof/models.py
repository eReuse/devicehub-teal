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
from ereuse_devicehub.resources.user import User


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
    device_id = db.Column(BigInteger,
                          db.ForeignKey(Device.id),
                          nullable=False)
    device = db.relationship(Device,
                             backref=db.backref('devices', uselist=True, lazy=True),
                             lazy=True,
                             primaryjoin=Device.id == device_id)

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



class ProofTransfer(JoinedTableMixin, Proof):
    supplier_id = db.Column(CIText(),
                         db.ForeignKey(User.ethereum_address),
                         nullable=False,
                         default=lambda: g.user.ethereum_address)
    supplier = db.relationship(User, primaryjoin=lambda: ProofTransfer.supplier_id == User.ethereum_address)
    receiver_id = db.Column(CIText(),
                         db.ForeignKey(User.ethereum_address),
                         nullable=False)
    receiver = db.relationship(User, primaryjoin=lambda: ProofTransfer.receiver_id == User.ethereum_address)
    deposit = Column(db.Integer, default=0)


class ProofDataWipe(JoinedTableMixin, Proof):
    erasure_type = Column(CIText(), default='', nullable=False)
    date = Column(db.DateTime, nullable=False, default=datetime.utcnow)
    result = Column(db.Boolean, default=False, nullable=False)
    result.comment = """Identifies proof datawipe as a result."""
    proof_author_id = Column(CIText(),
                          db.ForeignKey(User.ethereum_address),
                          nullable=False,
                          default=lambda: g.user.ethereum_address)
    proof_author = relationship(User, primaryjoin=lambda: ProofDataWipe.proof_author_id == User.ethereum_address)
    erasure_id = Column(UUID(as_uuid=True), ForeignKey(EraseBasic.id), nullable=False)
    erasure = relationship(EraseBasic,
                           backref=backref('proof_datawipe',
                                           lazy=True,
                                           uselist=False,
                                           cascade=CASCADE_OWN),
                           primaryjoin=EraseBasic.id == erasure_id)


class ProofFunction(JoinedTableMixin, Proof):
    disk_usage = Column(db.Integer, default=0)
    proof_author_id = Column(CIText(),
                          db.ForeignKey(User.ethereum_address),
                          nullable=False,
                          default=lambda: g.user.ethereum_address)
    proof_author = db.relationship(User, primaryjoin=lambda: ProofFunction.proof_author_id == User.ethereum_address)
    rate_id = Column(UUID(as_uuid=True), ForeignKey(Rate.id), nullable=False)
    rate = relationship(Rate,
                       backref=backref('proof_function',
                                       lazy=True,
                                       uselist=False,
                                       cascade=CASCADE_OWN),
                        primaryjoin=Rate.id == rate_id)


class ProofReuse(JoinedTableMixin, Proof):
    receiver_segment = Column(CIText(), default='', nullable=False)
    id_receipt = Column(CIText(), default='', nullable=False)
    supplier_id = db.Column(CIText(),
                         db.ForeignKey(User.ethereum_address),
                         nullable=False,
                         default=lambda: g.user.ethereum_address)
    supplier = db.relationship(User, primaryjoin=lambda: ProofReuse.supplier_id == User.ethereum_address)
    receiver_id = db.Column(CIText(),
                         db.ForeignKey(User.ethereum_address),
                         nullable=False)
    receiver = db.relationship(User, primaryjoin=lambda: ProofReuse.receiver_id == User.ethereum_address)
    price = Column(db.Integer)


class ProofRecycling(JoinedTableMixin, Proof):
    collection_point = Column(CIText(), default='', nullable=False)
    date = Column(db.DateTime, nullable=False, default=datetime.utcnow)
    contact = Column(CIText(), default='', nullable=False)
    ticket = Column(CIText(), default='', nullable=False)
    gps_location = Column(CIText(), default='', nullable=False)
    recycler_code = Column(CIText(), default='', nullable=False)
