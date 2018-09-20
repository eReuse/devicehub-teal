from base64 import b64decode
from uuid import UUID

import pytest
from sqlalchemy_utils import Password
from teal.enums import Country
from teal.marshmallow import ValidationError
from werkzeug.exceptions import NotFound

from ereuse_devicehub.client import Client
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.user import UserDef
from ereuse_devicehub.resources.user.exceptions import WrongCredentials
from ereuse_devicehub.resources.user.models import User
from tests.conftest import app_context, create_user


@pytest.mark.usefixtures(app_context.__name__)
def test_create_user_method_with_agent(app: Devicehub):
    """
    Tests creating an user through the main method.

    This method checks that the token is correct, too.
    """
    user_def = app.resources['User']  # type: UserDef
    u = user_def.create_user(email='foo@foo.com',
                             password='foo',
                             agent='Nice Person',
                             country=Country.ES.name,
                             telephone='+34 666 66 66 66',
                             tax_id='1234')
    user = User.query.filter_by(id=u['id']).one()  # type: User
    assert user.email == 'foo@foo.com'
    assert isinstance(user.token, UUID)
    assert User.query.filter_by(email='foo@foo.com').one() == user
    individual = next(iter(user.individuals))
    assert individual.name == 'Nice Person'
    assert individual.tax_id == '1234'
    assert individual.telephone.e164 == '+34666666666'
    assert individual.country == Country.ES
    assert individual.email == user.email


@pytest.mark.usefixtures(app_context.__name__)
def test_create_user_email_insensitive():
    """Ensures email is case insensitive."""
    user = User(email='FOO@foo.com')
    db.session.add(user)
    db.session.commit()
    # We search in case insensitive manner
    u1 = User.query.filter_by(email='foo@foo.com').one()
    assert u1 == user
    assert u1.email == 'foo@foo.com'


@pytest.mark.usefixtures(app_context.__name__)
def test_hash_password():
    """Tests correct password hashing and equaling."""
    user = create_user()
    assert isinstance(user.password, Password)
    assert user.password == 'foo'


def test_login_success(client: Client, app: Devicehub):
    """
    Tests successfully performing login.
    This checks that:

    - User is returned.
    - User has token.
    - User has not the password.
    """
    with app.app_context():
        create_user()
    user, _ = client.post({'email': 'foo@foo.com', 'password': 'foo'},
                          uri='/users/login',
                          status=200)
    assert user['email'] == 'foo@foo.com'
    assert UUID(b64decode(user['token'].encode()).decode()[:-1])
    assert 'password' not in user
    assert user['individuals'][0]['name'] == 'Timmy'
    assert user['individuals'][0]['type'] == 'Person'
    assert len(user['individuals']) == 1


def test_login_failure(client: Client, app: Devicehub):
    """Tests performing wrong login."""
    # Wrong password
    with app.app_context():
        create_user()
    client.post({'email': 'foo@foo.com', 'password': 'wrong pass'},
                uri='/users/login',
                status=WrongCredentials)
    # Wrong URI
    client.post({}, uri='/wrong-uri', status=NotFound)
    # Malformed data
    client.post({}, uri='/users/login', status=ValidationError)
    client.post({'email': 'this is not an email', 'password': 'nope'},
                uri='/users/login',
                status=ValidationError)
