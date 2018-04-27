import json as stdlib_json
from pathlib import Path

import pytest
import yaml

from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.user.models import User


class TestConfig(DevicehubConfig):
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/dh_test'
    SCHEMA = 'test'
    TESTING = True


@pytest.fixture(scope='module')
def config():
    return TestConfig()


@pytest.fixture(scope='module')
def _app(config: TestConfig) -> Devicehub:
    return Devicehub(config=config, db=db)


@pytest.fixture()
def app(request, _app: Devicehub) -> Devicehub:
    db.drop_all(app=_app)  # In case the test before was killed
    db.create_all(app=_app)
    # More robust than 'yield'
    request.addfinalizer(lambda *args, **kw: db.drop_all(app=_app))
    return _app


@pytest.fixture()
def client(app: Devicehub) -> Client:
    return app.test_client()


@pytest.fixture()
def user(app: Devicehub) -> UserClient:
    """Gets a client with a logged-in dummy user."""
    with app.app_context():
        user = create_user()
        client = UserClient(application=app,
                            response_wrapper=app.response_class,
                            email=user.email,
                            password='foo')
        client.user, _ = client.login(client.email, client.password)
        return client


def create_user(email='foo@foo.com', password='foo') -> User:
    user = User(email=email, password=password)
    db.session.add(user)
    db.session.commit()
    return user


def file(name: str) -> dict:
    """Opens and parses a JSON file from the ``files`` subdir."""
    with Path(__file__).parent.joinpath('files').joinpath(name + '.yaml').open() as f:
        return yaml.load(f)
