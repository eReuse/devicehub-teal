from itertools import chain
from operator import attrgetter
from uuid import uuid4

from flask import current_app as app, g
from sqlalchemy import Column, Enum as DBEnum, ForeignKey, Unicode, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import backref, relationship
from sqlalchemy_utils import EmailType, PhoneNumberType

from ereuse_devicehub.resources.models import STR_SIZE, STR_SM_SIZE, Thing
from ereuse_devicehub.resources.user.models import User
from teal import enums
from teal.db import INHERIT_COND, POLYMORPHIC_ID, \
    POLYMORPHIC_ON


class JoinedTableMixin:
    # noinspection PyMethodParameters
    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), ForeignKey(Agent.id), primary_key=True)


class Agent(Thing):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    type = Column(Unicode, nullable=False)
    name = Column(Unicode(length=STR_SM_SIZE))
    name.comment = """
        The name of the organization or person.
    """
    tax_id = Column(Unicode(length=STR_SM_SIZE))
    tax_id.comment = """
        The Tax / Fiscal ID of the organization, 
        e.g. the TIN in the US or the CIF/NIF in Spain.
    """
    country = Column(DBEnum(enums.Country))
    country.comment = """
        Country issuing the tax_id number.
    """
    telephone = Column(PhoneNumberType())
    email = Column(EmailType, unique=True)

    user_id = Column(UUID(as_uuid=True), ForeignKey(User.id), unique=True)
    user = relationship(User,
                        backref=backref('individuals', lazy=True, collection_class=set),
                        primaryjoin=user_id == User.id)

    __table_args__ = (
        UniqueConstraint(tax_id, country, name='Registration Number per country.'),
    )

    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Agent':
            args[POLYMORPHIC_ON] = cls.type
        if JoinedTableMixin in cls.mro():
            args[INHERIT_COND] = cls.id == Agent.id
        return args

    @property
    def events(self) -> list:
        # todo test
        return sorted(chain(self.events_agent, self.events_to), key=attrgetter('created'))

    def __repr__(self) -> str:
        return '<{0.t} {0.name}>'.format(self)


class Organization(JoinedTableMixin, Agent):
    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(**kwargs, name=name)

    @classmethod
    def get_default_org_id(cls) -> UUID:
        """Retrieves the default organization."""
        return g.setdefault('org_id',
                            Organization.query.filter_by(
                                **app.config.get_namespace('ORGANIZATION_')
                            ).one().id)


class Individual(JoinedTableMixin, Agent):
    active_org_id = Column(UUID(as_uuid=True), ForeignKey(Organization.id))
    active_org = relationship(Organization, primaryjoin=active_org_id == Organization.id)


class Membership(Thing):
    """Organizations that are related to the Individual.

    For example, because the individual works in or because is a member of.
    """
    id = Column(Unicode(length=STR_SIZE))
    organization_id = Column(UUID(as_uuid=True), ForeignKey(Organization.id), primary_key=True)
    organization = relationship(Organization,
                                backref=backref('members', collection_class=set, lazy=True),
                                primaryjoin=organization_id == Organization.id)
    individual_id = Column(UUID(as_uuid=True), ForeignKey(Individual.id), primary_key=True)
    individual = relationship(Individual,
                              backref=backref('member_of', collection_class=set, lazy=True),
                              primaryjoin=individual_id == Individual.id)

    def __init__(self, organization: Organization, individual: Individual, id: str = None) -> None:
        super().__init__(organization=organization,
                         individual=individual,
                         id=id)

    __table_args__ = (
        UniqueConstraint(id, organization_id, name='One member id per organization.'),
    )


class Person(Individual):
    """
    A person in the system. There can be several persons pointing to
    a real.
    """
    pass


class System(Individual):
    pass
