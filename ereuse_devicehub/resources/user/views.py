from uuid import UUID

from flask import g, request

from ereuse_devicehub.resources.user.exceptions import WrongCredentials
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.user.schemas import User as UserS
from teal.resource import View


class UserView(View):
    def one(self, id: UUID):
        return self.schema.jsonify(User.query.filter_by(id=id).one())


def login():
    # We use custom schema as we only want to parse a subset of user
    user_s = g.resource_def.SCHEMA(only=('email', 'password'))  # type: UserS
    # noinspection PyArgumentList
    u = request.get_json(schema=user_s)
    user = User.query.filter_by(email=u['email']).one_or_none()
    if user and user.password == u['password']:
        schema_with_token = g.resource_def.SCHEMA(exclude=set())
        return schema_with_token.jsonify(user)
    else:
        raise WrongCredentials()
