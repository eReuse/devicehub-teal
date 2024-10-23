import json
from uuid import uuid4

from citext import CIText
from ereuseapi.methods import API
from flask import current_app as app
from flask import g, session
from flask_login import UserMixin
from sqlalchemy import BigInteger, Boolean, Column, Sequence
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy_utils import EmailType, PasswordType

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.enums import SessionType
from ereuse_devicehub.resources.inventory.model import Inventory
from ereuse_devicehub.resources.models import STR_SIZE, Thing
from ereuse_devicehub.teal.db import CASCADE_OWN, URL, IntEnum


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
    api_keys_dlt = Column(CIText(), nullable=True)
    rols_dlt = Column(CIText(), nullable=True)
    inventories = db.relationship(
        Inventory,
        backref=db.backref('users', lazy=True, collection_class=set),
        secondary=lambda: UserInventory.__table__,
        collection_class=set,
    )

    # todo set restriction that user has, at least, one active db

    def get_user_id(self):
        return self.id

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

    def set_new_dlt_keys(self, data, password):
        if 'dpp' not in app.blueprints.keys():
            return ''

        from ereuse_devicehub.modules.dpp.utils import encrypt

        api_token = data.get('data', {}).get('api_token')
        data = json.dumps(data)
        self.api_keys_dlt = encrypt(password, data)
        return api_token

    def get_dlt_keys(self, password):
        if 'dpp' not in app.blueprints.keys():
            return {}

        from ereuse_devicehub.modules.dpp.utils import decrypt

        if not self.api_keys_dlt:
            return {}

        data = decrypt(password, self.api_keys_dlt)
        return json.loads(data)

    def reset_dlt_keys(self, password, data):
        if 'dpp' not in app.blueprints.keys():
            return

        from ereuse_devicehub.modules.dpp.utils import encrypt

        data = json.dumps(data)
        self.api_keys_dlt = encrypt(password, data)

    # # ==
    # def set_new_dlt_keys(self, password):
    #     if 'dpp' not in app.blueprints.keys():
    #         return

    #     from ereuseapi.methods import register_user

    #     from ereuse_devicehub.modules.dpp.utils import encrypt

    #     api_dlt = app.config.get('API_DLT')
    #     data = register_user(api_dlt)
    #     api_token = data.get('data', {}).get('api_token')
    #     data = json.dumps(data)
    #     self.api_keys_dlt = encrypt(password, data)
    #     return api_token

    # def get_dlt_keys(self, password):
    #     if 'dpp' not in app.blueprints.keys():
    #         return {}

    #     from ereuse_devicehub.modules.dpp.utils import decrypt

    #     if not self.api_keys_dlt:
    #         return {}

    #     data = decrypt(password, self.api_keys_dlt)
    #     return json.loads(data)

    # def reset_dlt_keys(self, password, data):
    #     if 'dpp' not in app.blueprints.keys():
    #         return

    #     from ereuse_devicehub.modules.dpp.utils import encrypt

    #     data = json.dumps(data)
    #     self.api_keys_dlt = encrypt(password, data)
        
    def allow_permitions(self, api_token=None, rols="Operator"):
        if 'dpp' not in app.blueprints.keys():
            return

        if not api_token:
            api_token = session.get('token_dlt', '.')
        target_user = api_token.split(".")[0]
        keyUser1 = app.config.get('API_DLT_TOKEN')
        api_dlt = app.config.get('API_DLT')
        if not keyUser1 or not api_dlt:
            return

        apiUser1 = API(api_dlt, keyUser1, "ethereum")

        for rol in rols.split(","):
            result = apiUser1.issue_credential(rol.strip(), target_user)
        return result

    def get_rols_dlt(self):
        if not self.rols_dlt:
            return []
        return json.loads(self.rols_dlt)

    def set_rols_dlt(self, token_dlt=None):
        rols = self.get_rols(self, token_dlt=token_dlt)
        if rols:
            self.rols_dlt = json.dumps(rols)
        return rols

    def get_rols(self, token_dlt=None):

        if 'dpp' not in app.blueprints.keys():
            return []

        if not token_dlt:
            token_dlt = session.get('token_dlt')
            if not token_dlt:
                return []

        api_dlt = app.config.get('API_DLT')
        if not api_dlt:
            return []

        api = API(api_dlt, token_dlt, "ethereum")

        result = api.check_user_roles()
        if result.get('Status') != 200:
            return []

        if 'Success' not in result.get('Data', {}).get('status'):
            return []

        rols = result.get('Data', {}).get('data', {})
        return [(k, k) for k, v in rols.items() if v]


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


class SanitizationEntity(Thing):
    id = db.Column(BigInteger, primary_key=True)
    company_name = db.Column(db.String, nullable=True)
    location = db.Column(db.String, nullable=True)
    # logo = db.Column(db.String, nullable=True)
    logo = db.Column(URL(), nullable=True)
    responsable_person = db.Column(db.String, nullable=True)
    supervisor_person = db.Column(db.String, nullable=True)
    user_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey(User.id),
        default=lambda: g.user.id,
    )
    user = db.relationship(
        User,
        backref=db.backref(
            'sanitization_entity', lazy=True, uselist=False, cascade=CASCADE_OWN
        ),
        primaryjoin=user_id == User.id,
    )

    def __str__(self) -> str:
        return '{0.company_name}'.format(self)
