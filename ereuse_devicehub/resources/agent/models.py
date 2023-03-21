from itertools import chain
from operator import attrgetter
from uuid import uuid4

from citext import CIText
from sqlalchemy import Column
from sqlalchemy import Enum as DBEnum
from sqlalchemy import ForeignKey, Unicode, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy_utils import EmailType, PhoneNumberType

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.inventory import Inventory
from ereuse_devicehub.resources.models import STR_SM_SIZE, Thing
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.teal import enums
from ereuse_devicehub.teal.db import (
    INHERIT_COND,
    POLYMORPHIC_ID,
    POLYMORPHIC_ON,
    check_lower,
)
from ereuse_devicehub.teal.marshmallow import ValidationError


class JoinedTableMixin:
    # noinspection PyMethodParameters
    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), ForeignKey(Agent.id), primary_key=True)


class Agent(Thing):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    type = Column(Unicode, nullable=False)
    name = Column(CIText())
    name.comment = """The name of the organization or person."""
    tax_id = Column(Unicode(length=STR_SM_SIZE), check_lower('tax_id'))
    tax_id.comment = """The Tax / Fiscal ID of the organization,
    e.g. the TIN in the US or the CIF/NIF in Spain.
    """
    country = Column(DBEnum(enums.Country))
    country.comment = """Country issuing the tax_id number."""
    telephone = Column(PhoneNumberType())
    email = Column(EmailType, unique=True)

    __table_args__ = (
        UniqueConstraint(tax_id, country, name='Registration Number per country.'),
        UniqueConstraint(tax_id, name, name='One tax ID with one name.'),
        db.Index('agent_type', type, postgresql_using='hash'),
    )

    @declared_attr
    def __mapper_args__(cls):
        """Defines inheritance.

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
    def actions(self) -> list:
        # todo test
        return sorted(
            chain(self.actions_agent, self.actions_to), key=attrgetter('created')
        )

    @validates('name')
    def does_not_contain_slash(self, _, value: str):
        if '/' in value:
            raise ValidationError('Name cannot contain slash \'')
        return value

    def __repr__(self) -> str:
        return '<{0.t} {0.name}>'.format(self)


class Organization(JoinedTableMixin, Agent):
    default_of = db.relationship(
        Inventory,
        uselist=False,
        lazy=True,
        backref=backref('org', lazy=True),
        # We need to use this as we cannot do Inventory.foreign -> Org
        # as foreign keys can only reference to one table
        # and we have multiple organization table (one per schema)
        foreign_keys=[Inventory.org_id],
        primaryjoin=lambda: Organization.id == Inventory.org_id,
    )

    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(**kwargs, name=name)

    @classmethod
    def get_default_org_id(cls) -> UUID:
        """Retrieves the default organization."""
        return cls.query.filter_by(default_of=Inventory.current).one().id


class Individual(JoinedTableMixin, Agent):
    active_org_id = Column(UUID(as_uuid=True), ForeignKey(Organization.id))

    active_org = relationship(
        Organization, primaryjoin=active_org_id == Organization.id
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey(User.id), unique=True)
    user = relationship(
        User,
        backref=backref('individuals', lazy=True, collection_class=set),
        primaryjoin=user_id == User.id,
    )


class Membership(Thing):
    """Organizations that are related to the Individual.

    For example, because the individual works in or because is a member of.
    """

    id = Column(Unicode(), check_lower('id'))
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey(Organization.id), primary_key=True
    )
    organization = relationship(
        Organization,
        backref=backref('members', collection_class=set, lazy=True),
        primaryjoin=organization_id == Organization.id,
    )
    individual_id = Column(
        UUID(as_uuid=True), ForeignKey(Individual.id), primary_key=True
    )
    individual = relationship(
        Individual,
        backref=backref('member_of', collection_class=set, lazy=True),
        primaryjoin=individual_id == Individual.id,
    )

    def __init__(
        self, organization: Organization, individual: Individual, id: str = None
    ) -> None:
        super().__init__(organization=organization, individual=individual, id=id)

    __table_args__ = (
        UniqueConstraint(id, organization_id, name='One member id per organization.'),
    )


class Person(Individual):
    """A person in the system. There can be several persons pointing to
    a real.
    """

    pass


class System(Individual):
    pass
