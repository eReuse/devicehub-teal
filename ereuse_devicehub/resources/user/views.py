from uuid import UUID, uuid4

from flask import g, request
from flask.json import jsonify
from teal.resource import View

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.exceptions import WrongCredentials
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.user.schemas import User as UserS


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


def logout():
    # We use custom schema as we only want to parse a subset of user
    g.user.token = uuid4()
    db.session.add(g.user)
    db.session.commit()
    return jsonify('Ok')
