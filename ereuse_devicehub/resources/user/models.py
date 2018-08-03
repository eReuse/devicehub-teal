from uuid import uuid4

from flask import current_app as app
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy_utils import EmailType, PasswordType

from ereuse_devicehub.resources.models import STR_SIZE, Thing


class User(Thing):
    __table_args__ = {'schema': 'common'}
    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True)
    email = Column(EmailType, nullable=False, unique=True)
    password = Column(PasswordType(max_length=STR_SIZE,
                                   onload=lambda **kwargs: dict(
                                       schemes=app.config['PASSWORD_SCHEMES'],
                                       **kwargs
                                   )))
    """
    Password field.
    From `here <https://sqlalchemy-utils.readthedocs.io/en/latest/
    data_types.html#module-sqlalchemy_utils.types.password>`_
    """
    token = Column(UUID(as_uuid=True), default=uuid4, unique=True)

    def __repr__(self) -> str:
        return '<User {0.email}>'.format(self)

    @property
    def individual(self):
        """The individual associated for this database, or None."""
        return next(iter(self.individuals), None)
