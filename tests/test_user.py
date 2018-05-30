from base64 import b64decode
from uuid import UUID

from sqlalchemy_utils import Password
from werkzeug.exceptions import NotFound

from ereuse_devicehub.client import Client
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.user import UserDef
from ereuse_devicehub.resources.user.exceptions import WrongCredentials
from ereuse_devicehub.resources.user.models import User
from teal.marshmallow import ValidationError
from tests.conftest import create_user


def test_create_user_method(app: Devicehub):
    """
    Tests creating an user through the main method.

    This method checks that the token is correct, too.
    """
    with app.app_context():
        user_def = app.resources['User']  # type: UserDef
        u = user_def.create_user(email='foo@foo.com', password='foo')
        user = User.query.filter_by(id=u['id']).one()  # type: User
        assert user.email == 'foo@foo.com'
        assert isinstance(user.token, UUID)
        assert User.query.filter_by(email='foo@foo.com').one() == user


def test_create_user_email_insensitive(app: Devicehub):
    """Ensures email is case insensitive."""
    with app.app_context():
        user = User(email='FOO@foo.com')
        db.session.add(user)
        db.session.commit()
        # We search in case insensitive manner
        u1 = User.query.filter_by(email='foo@foo.com').one()
        assert u1 == user
        assert u1.email == 'foo@foo.com'


def test_hash_password(app: Devicehub):
    """Tests correct password hashing and equaling."""
    with app.app_context():
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
