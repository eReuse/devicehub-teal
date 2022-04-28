from uuid import uuid4

from flask import current_app as app
from flask_login import UserMixin
from sqlalchemy import BigInteger, Boolean, Column, Sequence
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy_utils import EmailType, PasswordType
from teal.db import IntEnum

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.enums import SessionType
from ereuse_devicehub.resources.inventory.model import Inventory
from ereuse_devicehub.resources.models import STR_SIZE, Thing


class User(UserMixin, Thing):
    __table_args__ = {'schema': 'common'}
    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True)
    email = Column(EmailType, nullable=False, unique=True)
    password = Column(
        PasswordType(
            max_length=STR_SIZE,
            onload=lambda **kwargs: dict(
                schemes=app.config['PASSWORD_SCHEMES'], **kwargs
            ),
        )
    )
    token = Column(UUID(as_uuid=True), default=uuid4, unique=True, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    phantom = Column(Boolean, default=False, nullable=False)
    inventories = db.relationship(
        Inventory,
        backref=db.backref('users', lazy=True, collection_class=set),
        secondary=lambda: UserInventory.__table__,
        collection_class=set,
    )

    # todo set restriction that user has, at least, one active db

    def __init__(
        self, email, password=None, inventories=None, active=True, phantom=False
    ) -> None:
        """Creates an user.
        :param email:
        :param password:
        :param inventories: A set of Inventory where the user has
        access to. If none, the user is granted access to the current
        inventory.
        :param active: allow active and deactive one account without delete the account
        :param phantom: it's util for identify the phantom accounts
        create during the trade actions
        """
        inventories = inventories or {Inventory.current}
        super().__init__(
            email=email,
            password=password,
            inventories=inventories,
            active=active,
            phantom=phantom,
        )

    def __repr__(self) -> str:
        return '<User {0.email}>'.format(self)

    @property
    def type(self) -> str:
        return self.__class__.__name__

    @property
    def individual(self):
        """The individual associated for this database, or None."""
        return next(iter(self.individuals), None)

    @property
    def code(self):
        """Code of phantoms accounts"""
        if not self.phantom:
            return
        return self.email.split('@')[0].split('_')[1]

    @property
    def is_active(self):
        """Alias because flask-login expects `is_active` attribute"""
        return self.active

    @property
    def get_full_name(self):
        # TODO(@slamora) create first_name & last_name fields???
        # needs to be discussed related to Agent <--> User concepts
        return self.email

    def check_password(self, password):
        # take advantage of SQL Alchemy PasswordType to verify password
        return self.password == password


class UserInventory(db.Model):
    """Relationship between users and their inventories."""

    __table_args__ = {'schema': 'common'}
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey(User.id), primary_key=True)
    inventory_id = db.Column(
        db.Unicode(), db.ForeignKey(Inventory.id), primary_key=True
    )


class Session(Thing):
    __table_args__ = {'schema': 'common'}
    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)
    expired = Column(BigInteger, default=0)
    token = Column(UUID(as_uuid=True), default=uuid4, unique=True, nullable=False)
    type = Column(IntEnum(SessionType), default=SessionType.Internal, nullable=False)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey(User.id))
    user = db.relationship(
        User,
        backref=db.backref('sessions', lazy=True, collection_class=set),
        collection_class=set,
    )

    def __str__(self) -> str:
        return '{0.token}'.format(self)
