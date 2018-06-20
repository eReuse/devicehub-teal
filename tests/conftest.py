from pathlib import Path

import pytest
import yaml

from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.tag import Tag
from ereuse_devicehub.resources.user.models import User


class TestConfig(DevicehubConfig):
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/dh_test'
    SCHEMA = 'test'
    TESTING = True
    ORGANIZATION_NAME = 'FooOrg'
    ORGANIZATION_TAX_ID = 'FooOrgId'


@pytest.fixture(scope='module')
def config():
    return TestConfig()


@pytest.fixture(scope='module')
def _app(config: TestConfig) -> Devicehub:
    return Devicehub(config=config, db=db)


@pytest.fixture()
def app(request, _app: Devicehub) -> Devicehub:
    with _app.app_context():
        _app.init_db()
    # More robust than 'yield'
    request.addfinalizer(lambda *args, **kw: db.drop_all(app=_app))
    return _app


@pytest.fixture()
def client(app: Devicehub) -> Client:
    return app.test_client()


@pytest.fixture()
def app_context(app: Devicehub):
    with app.app_context():
        yield


@pytest.fixture()
def user(app: Devicehub) -> UserClient:
    """Gets a client with a logged-in dummy user."""
    with app.app_context():
        password = 'foo'
        user = create_user(password=password)
        client = UserClient(application=app,
                            response_wrapper=app.response_class,
                            email=user.email,
                            password=password)
        client.user, _ = client.login(client.email, client.password)
        return client


def create_user(email='foo@foo.com', password='foo') -> User:
    user = User(email=email, password=password)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def auth_app_context(app: Devicehub):
    """Creates an app context with a set user."""
    with app.app_context():
        user = create_user()

        class Auth:  # Mock
            username = user.token
            password = ''

        app.auth.perform_auth(Auth())
        yield


def file(name: str) -> dict:
    """Opens and parses a YAML file from the ``files`` subdir."""
    with Path(__file__).parent.joinpath('files').joinpath(name + '.yaml').open() as f:
        return yaml.load(f)


@pytest.fixture()
def tag_id(app: Devicehub) -> str:
    """Creates a tag and returns its id."""
    with app.app_context():
        t = Tag(id='foo')
        db.session.add(t)
        db.session.commit()
        return t.id
