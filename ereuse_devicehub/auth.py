from sqlalchemy.exc import DataError
from werkzeug.exceptions import Unauthorized

from ereuse_devicehub.resources.user.models import User
from teal.auth import TokenAuth
from teal.db import ResourceNotFound


class Auth(TokenAuth):
    def authenticate(self, token: str, *args, **kw) -> User:
        try:
            return User.query.filter_by(token=token).one()
        except (ResourceNotFound, DataError):
            raise Unauthorized('Provide a suitable token.')
