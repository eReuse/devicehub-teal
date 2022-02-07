from unittest.mock import Mock

import pytest

from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.dispatchers import PathDispatcher
from tests.conftest import TestConfig


def noop():
    pass


@pytest.mark.mvp
@pytest.fixture()
def dispatcher(app: Devicehub, config: TestConfig) -> PathDispatcher:
    PathDispatcher.call = Mock(side_effect=lambda *args: args[0])
    return PathDispatcher(config_cls=config)


@pytest.mark.mvp
def test_dispatcher_default(dispatcher: PathDispatcher):
    """The dispatcher returns not found for an URL that does not
    route to an app.
    """
    app = dispatcher({'SCRIPT_NAME:': '/', 'PATH_INFO': '/'}, noop)
    assert app == PathDispatcher.NOT_FOUND
    app = dispatcher({'SCRIPT_NAME:': '/', 'PATH_INFO': '/foo/foo'}, noop)
    assert app == PathDispatcher.NOT_FOUND


@pytest.mark.mvp
def test_dispatcher_return_app(dispatcher: PathDispatcher):
    """The dispatcher returns the correct app for the URL."""
    # Note that the dispatcher does not check if the URL points
    # to a well-known endpoint for the app.
    # Only if can route it to an app. And then the app checks
    # if the path exists
    app = dispatcher({'SCRIPT_NAME:': '/', 'PATH_INFO': '/test/foo/'}, noop)
    assert isinstance(app, Devicehub)
    assert app.id == 'test'


@pytest.mark.mvp
def test_dispatcher_users(dispatcher: PathDispatcher):
    """Users special endpoint returns an app."""
    # For now returns the first app, as all apps
    # can answer {}/users/login
    app = dispatcher({'SCRIPT_NAME:': '/', 'PATH_INFO': '/users/'}, noop)
    assert isinstance(app, Devicehub)
    assert app.id == 'test'
