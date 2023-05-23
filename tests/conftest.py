import io
import json
import uuid
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

import boltons.urlutils
import jwt
import pytest
import yaml
from decouple import config
from psycopg2 import IntegrityError
from sqlalchemy.exc import ProgrammingError

from ereuse_devicehub import ereuse_utils
from ereuse_devicehub.api.views import api
from ereuse_devicehub.client import Client, UserClient, UserClientFlask
from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.inventory.views import devices
from ereuse_devicehub.labels.views import labels
from ereuse_devicehub.mail.flask_mail import Mail
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.enums import SessionType
from ereuse_devicehub.resources.tag import Tag
from ereuse_devicehub.resources.user.models import Session, User
from ereuse_devicehub.views import core
from ereuse_devicehub.workbench.views import workbench

STARTT = datetime(year=2000, month=1, day=1, hour=1)
"""A dummy starting time to use in tests."""
ENDT = datetime(year=2000, month=1, day=1, hour=2)
"""A dummy ending time to use in tests."""
T = {'start_time': STARTT, 'end_time': ENDT}
"""A dummy start_time/end_time to use as function keywords."""
P = config('JWT_PASS', '')


class TestConfig(DevicehubConfig):
    SQLALCHEMY_DATABASE_URI = 'postgresql://dhub:ereuse@localhost/dh_test'
    TESTING = True
    SERVER_NAME = 'localhost'
    TMP_SNAPSHOTS = '/tmp/snapshots'
    TMP_LIVES = '/tmp/lives'
    EMAIL_ADMIN = 'foo@foo.com'
    PATH_DOCUMENTS_STORAGE = '/tmp/trade_documents'
    JWT_PASS = config('JWT_PASS', '')
    MAIL_SUPPRESS_SEND = True


@pytest.fixture(scope='session')
def config():
    return TestConfig()


@pytest.fixture(scope='session')
def _app(config: TestConfig) -> Devicehub:
    # dh_config = DevicehubConfig()
    # config = TestConfig(dh_config)
    app = Devicehub(inventory='test', config=config, db=db)
    app.register_blueprint(core)
    app.register_blueprint(devices)
    app.register_blueprint(labels)
    app.register_blueprint(api)
    app.register_blueprint(workbench)
    app.config["SQLALCHEMY_RECORD_QUERIES"] = True
    app.config['PROFILE'] = True
    app.config['SCHEMA'] = 'test'
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
    mail = Mail(app)
    app.mail = mail
    return app


@pytest.fixture(scope='session')
def _app2(config: TestConfig) -> Devicehub:
    return Devicehub(inventory='test', config=config, db=db)


@pytest.fixture()
def app(request, _app: Devicehub) -> Devicehub:
    # More robust than 'yield'
    def _drop(*args, **kwargs):
        with _app.app_context():
            db.drop_all()

    def _init():
        _app.init_db(
            name='Test Inventory',
            org_name='FooOrg',
            org_id='foo-org-id',
            tag_url=boltons.urlutils.URL('https://example.com'),
            tag_token=uuid.UUID('52dacef0-6bcb-4919-bfed-f10d2c96ecee'),
            erase=False,
            common=True,
        )

    with _app.app_context():
        try:
            with redirect_stdout(io.StringIO()):
                _init()
        except (ProgrammingError, IntegrityError, AssertionError):
            print('Database was not correctly emptied. Re-empty and re-installing...')
            _drop()
            _init()

    request.addfinalizer(_drop)
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
        client = UserClient(
            app, user.email, password, response_wrapper=app.response_class
        )
        client.login()
        return client


@pytest.fixture()
def user2(app: Devicehub) -> UserClient:
    """Gets a client with a logged-in dummy user."""
    with app.app_context():
        password = 'foo'
        email = 'foo2@foo.com'
        user = create_user(email=email, password=password)
        client = UserClient(
            app, user.email, password, response_wrapper=app.response_class
        )
        client.login()
        return client


@pytest.fixture()
def user3(app: Devicehub) -> UserClientFlask:
    """Gets a client with a logged-in dummy user."""
    with app.app_context():
        password = 'foo'
        user = create_user(password=password)
        client = UserClientFlask(app, user.email, password)
        return client


@pytest.fixture()
def user4(app: Devicehub) -> UserClient:
    """Gets a client with a logged-in dummy user."""
    with app.app_context():
        password = 'foo'
        email = 'foo2@foo.com'
        user = create_user(email=email, password=password)
        client = UserClientFlask(app, user.email, password)
        return client


def create_user(email='foo@foo.com', password='foo') -> User:
    user = User(email=email, password=password)
    user.individuals.add(Person(name='Timmy'))
    session_external = Session(user=user, type=SessionType.External)
    session_internal = Session(user=user, type=SessionType.Internal)
    db.session.add(user)
    db.session.add(session_internal)
    db.session.add(session_external)
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
        yield app


def json_encode(dev: str) -> dict:
    """Encode json."""
    data = {"type": "Snapshot"}
    data['data'] = jwt.encode(
        dev, P, algorithm="HS256", json_encoder=ereuse_utils.JSONEncoder
    )

    return data


def yaml2json(name: str) -> dict:
    """Opens and parses a YAML file from the ``files`` subdir."""
    with Path(__file__).parent.joinpath('files').joinpath(name + '.yaml').open() as f:
        return yaml.load(f)


def file(name: str) -> dict:
    """Opens and parses a YAML file from the ``files`` subdir. And decode"""
    return json_encode(yaml2json(name))


def file_json(name):
    with Path(__file__).parent.joinpath('files').joinpath(name).open() as f:
        return json.loads(f.read())


def file_workbench(name: str) -> dict:
    """Opens and parses a YAML file from the ``files`` subdir."""
    with Path(__file__).parent.joinpath('workbench_files').joinpath(
        name + '.json'
    ).open() as f:
        return yaml.load(f)


@pytest.fixture()
def tag_id(app: Devicehub) -> str:
    """Creates a tag and returns its id."""
    with app.app_context():
        if User.query.count():
            user = User.query.one()
        else:
            user = create_user()
        t = Tag(id='foo', owner_id=user.id)
        db.session.add(t)
        db.session.commit()
        return t.id
