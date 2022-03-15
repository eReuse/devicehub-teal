import pytest
from flask.testing import FlaskClient
from flask_wtf.csrf import generate_csrf

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.devicehub import Devicehub
from tests import conftest


@pytest.mark.mvp
# @pytest.mark.usefixtures()
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_login(user: UserClient, app: Devicehub):
    """Checks a simple login"""

    client = FlaskClient(app, use_cookies=True)

    body, status, headers = client.get('/login/')
    body = next(body).decode("utf-8")
    assert status == '200 OK'
    assert "Login to Your Account" in body

    data = {
        'email': user.email,
        'password': 'foo',
        'remember': False,
        'csrf_token': generate_csrf(),
    }
    body, status, headers = client.post('/login/', data=data, follow_redirects=True)

    body = next(body).decode("utf-8")
    assert status == '200 OK'
    assert "Login to Your Account" not in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_inventory(user: UserClient, app: Devicehub):
    client = FlaskClient(app, use_cookies=True)
    client.get('/login/')
    data = {
        'email': user.email,
        'password': 'foo',
        'remember': False,
        'csrf_token': generate_csrf(),
    }
    body, status, headers = client.post('/login/', data=data, follow_redirects=True)
    body, status, headers = client.get('/inventory/device/', headers=headers)

    body = next(body).decode("utf-8")
    assert status == '200 OK'
    # import pdb; pdb.set_trace()
    assert "Unassgined" in body
