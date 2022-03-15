# import pytest
from flask.testing import FlaskClient

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.devicehub import Devicehub

# from tests import conftest


# @pytest.mark.mvp
# @pytest.mark.usefixtures()
# def test_create_application(client: FlaskClient, mocker):
# @pytest.mark.usefixtures(conftest.app_context.__name__)
def test_login(user: UserClient, app: Devicehub):
    """Checks a simple login"""

    client = FlaskClient(app, use_cookies=True, response_wrapper=app.response_class)
    body, status, headers = client.get('/login/')
    body = next(body).decode("utf-8")
    assert status == '200 OK'
    assert "Login to Your Account" in body

    data = {'email': user.email, 'password': 'foo', "remember": False}
    body, status, headers = client.post('/login/', data=data)

    body = next(body).decode("utf-8")
    assert status == '200 OK'
    assert "Login to Your Account" not in body
