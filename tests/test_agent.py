from uuid import UUID

import pytest
from marshmallow import ValidationError
from sqlalchemy_utils import PhoneNumber

from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.agent import OrganizationDef, models, schemas
from ereuse_devicehub.resources.agent.models import (
    Membership,
    Organization,
    Person,
    System,
)
from ereuse_devicehub.teal.db import DBError, UniqueViolation
from ereuse_devicehub.teal.enums import Country
from tests.conftest import app_context, create_user


@pytest.mark.usefixtures(app_context.__name__)
def test_agent():
    """Tests creating an person."""
    person = Person(
        name='Timmy',
        tax_id='xyz',
        country=Country.ES,
        telephone=PhoneNumber('+34666666666'),
        email='foo@bar.com',
    )
    db.session.add(person)
    db.session.commit()

    p = schemas.Person().dump(person)
    assert p['name'] == person.name == 'Timmy'
    assert p['taxId'] == person.tax_id == 'xyz'
    assert p['country'] == person.country.name == 'ES'
    assert p['telephone'] == person.telephone.international == '+34 666 66 66 66'
    assert p['email'] == person.email == 'foo@bar.com'


@pytest.mark.usefixtures(app_context.__name__)
def test_system():
    """Tests creating a system."""
    system = System(name='Workbench', email='hello@ereuse.org')
    db.session.add(system)
    db.session.commit()

    s = schemas.System().dump(system)
    assert s['name'] == system.name == 'Workbench'
    assert s['email'] == system.email == 'hello@ereuse.org'


@pytest.mark.usefixtures(app_context.__name__)
def test_organization():
    """Tests creating an organization."""
    org = Organization(
        name='ACME', tax_id='xyz', country=Country.ES, email='contact@acme.com'
    )
    db.session.add(org)
    db.session.commit()

    o = schemas.Organization().dump(org)
    assert o['name'] == org.name == 'ACME'
    assert o['taxId'] == org.tax_id == 'xyz'
    assert org.country.name == o['country'] == 'ES'


@pytest.mark.usefixtures(app_context.__name__)
def test_membership():
    """Tests assigning an Individual to an Organization."""
    person = Person(name='Timmy')
    org = Organization(name='ACME')
    person.member_of.add(Membership(org, person, id='acme-1'))
    db.session.add(person)
    db.session.flush()


@pytest.mark.usefixtures(app_context.__name__)
def test_membership_repeated():
    person = Person(name='Timmy')
    org = Organization(name='ACME')
    person.member_of.add(Membership(org, person, id='acme-1'))
    db.session.add(person)

    person.member_of.add(Membership(org, person))
    with pytest.raises(DBError):
        db.session.flush()


@pytest.mark.usefixtures(app_context.__name__)
def test_membership_repeating_id():
    person = Person(name='Timmy')
    org = Organization(name='ACME')
    person.member_of.add(Membership(org, person, id='acme-1'))
    db.session.add(person)
    db.session.flush()

    person2 = Person(name='Tommy')
    person2.member_of.add(Membership(org, person2, id='acme-1'))
    db.session.add(person2)
    with pytest.raises(DBError) as e:
        db.session.flush()
    assert 'One member id per organization' in str(e)


@pytest.mark.usefixtures(app_context.__name__)
def test_default_org_exists(config: DevicehubConfig):
    """Ensures that the default organization is created on app
    initialization and that is accessible for the method
    :meth:`ereuse_devicehub.resources.user.Organization.get_default_org`.
    """
    assert models.Organization.query.filter_by(name='FooOrg', tax_id='foo-org-id').one()
    assert isinstance(models.Organization.get_default_org_id(), UUID)


@pytest.mark.usefixtures(app_context.__name__)
def test_assign_individual_user():
    """Tests assigning an individual to an user."""
    user = create_user()
    assert len(user.individuals) == 1
    assert next(iter(user.individuals)).name == 'Timmy'


@pytest.mark.usefixtures(app_context.__name__)
def test_create_organization_main_method(app: Devicehub):
    org_def = app.resources[models.Organization.t]  # type: OrganizationDef
    o = org_def.create_org('ACME', tax_id='foo', country='ES')
    org = models.Agent.query.filter_by(id=o['id']).one()  # type: Organization
    assert org.name == o['name'] == 'ACME'
    assert org.tax_id == o['taxId'] == 'foo', 'FOO must be converted to lowercase'
    assert org.country.name == o['country'] == 'ES'


@pytest.mark.usefixtures(app_context.__name__)
def test_organization_no_slash_name():
    with pytest.raises(ValidationError):
        Organization(name='/')
