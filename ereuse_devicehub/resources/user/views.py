from uuid import UUID

from flask import current_app as app, request

from ereuse_devicehub.resources.user.exceptions import WrongCredentials
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.user.schemas import User as UserS
from teal.resource import View


class UserView(View):
    def one(self, id: UUID):
        return self.schema.jsonify(User.query.filter_by(id=id).one())


def login():
    user_s = app.resources['User'].schema  # type: UserS
    u = user_s.load(request.get_json(), partial=('email', 'password'))
    user = User.query.filter_by(email=u['email']).one_or_none()
    if user and user.password == u['password']:
        return user_s.jsonify(user)
    else:
        raise WrongCredentials()
