from uuid import uuid4

from flask import current_app as app, g
from sqlalchemy import Column, Unicode, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy_utils import CountryType, EmailType, PasswordType

from ereuse_devicehub.resources.models import STR_SIZE, STR_SM_SIZE, Thing


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
    name = Column(Unicode(length=STR_SIZE))
    token = Column(UUID(as_uuid=True), default=uuid4, unique=True)

    def __repr__(self) -> str:
        return '<{0.t} {0.id} email={0.email}>'.format(self)


class Organization(Thing):
    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True)
    name = Column(Unicode(length=STR_SM_SIZE), unique=True)
    tax_id = Column(Unicode(length=STR_SM_SIZE),
                    comment='The Tax / Fiscal ID of the organization, '
                            'e.g. the TIN in the US or the CIF/NIF in Spain.')
    country = Column(CountryType, comment='Country issuing the tax_id number.')

    __table_args__ = (
        UniqueConstraint(tax_id, country, name='Registration Number per country.'),
    )

    @classmethod
    def get_default_org_id(cls) -> UUID:
        """Retrieves the default organization."""
        return g.setdefault('org_id',
                            Organization.query.filter_by(
                                **app.config.get_namespace('ORGANIZATION_')
                            ).one().id)

    def __repr__(self) -> str:
        return '<Org {0.id}: {0.name}>'.format(self)
