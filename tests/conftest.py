import pytest

from ereuse_devicehub.client import Client
from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub


class TestConfig(DevicehubConfig):
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/dh_test'
    SQLALCHEMY_BINDS = {
        'common': 'postgresql://localhost/dh_test_common'
    }


@pytest.fixture()
def config():
    return TestConfig()


@pytest.fixture()
def app(config: TestConfig) -> Devicehub:
    app = Devicehub(config=config, db=db)
    db.create_all(app=app)
    yield app
    db.drop_all(app=app)


@pytest.fixture()
def client(app: Devicehub) -> Client:
    return app.test_client()
