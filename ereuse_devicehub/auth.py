from sqlalchemy.exc import DataError
from werkzeug.exceptions import Unauthorized

from ereuse_devicehub.resources.user.models import Session, User
from ereuse_devicehub.teal.auth import TokenAuth
from ereuse_devicehub.teal.db import ResourceNotFound


class Auth(TokenAuth):
    def authenticate(self, token: str, *args, **kw) -> User:
        try:
            user = User.query.filter_by(token=token).first()
            if user:
                return user

            ses = Session.query.filter_by(token=token).one()
            return ses.user
        except (ResourceNotFound, DataError):
            raise Unauthorized('Provide a suitable token.')
