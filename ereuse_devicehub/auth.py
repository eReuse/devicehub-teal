from sqlalchemy.exc import DataError
from teal.auth import TokenAuth
from teal.db import ResourceNotFound
from werkzeug.exceptions import Unauthorized

from ereuse_devicehub.resources.user.models import User, Session


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
