from uuid import uuid4

import pytest
from werkzeug.exceptions import Unauthorized

from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.devicehub import Devicehub
from tests.conftest import create_user


@pytest.mark.mvp
def test_authenticate_success(app: Devicehub):
    """Checks the authenticate method."""
    with app.app_context():
        user = create_user()
        response_user = app.auth.authenticate(token=str(user.token))
        assert response_user == user


@pytest.mark.mvp
def test_authenticate_error(app: Devicehub):
    """Tests the authenticate method with wrong token values."""
    with app.app_context():
        create_user()
        # Token doesn't exist
        with pytest.raises(Unauthorized):
            app.auth.authenticate(token=str(uuid4()))
            pytest.fail('Provide a suitable token.')


@pytest.mark.mvp
def test_authenticate_error_malformed_token(app: Devicehub):
    """Tests the authenticate method with malformed token."""
    with app.app_context():
        create_user()
        # Wrong token format
        with pytest.raises(Unauthorized):
            app.auth.authenticate(token='this is a wrong uuid')
            pytest.fail('Provide a suitable token.')


@pytest.mark.mvp
def test_auth_view(user: UserClient, client: Client):
    """Tests authentication at endpoint / view."""
    user.get(res='User', item=user.user['id'], status=200)
    client.get(res='User', item=user.user['id'], status=Unauthorized)
    client.get(
        res='User', item=user.user['id'], token='wrong token', status=Unauthorized
    )
