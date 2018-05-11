from click import argument, option

from ereuse_devicehub import devicehub
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.user.schemas import User as UserS
from ereuse_devicehub.resources.user.views import UserView, login
from teal.resource import Converters, Resource


class UserDef(Resource):
    SCHEMA = UserS
    VIEW = UserView
    ID_CONVERTER = Converters.uid
    AUTH = True

    def __init__(self, app: 'devicehub.Devicehub', import_name=__package__, static_folder=None,
                 static_url_path=None, template_folder=None, url_prefix=None, subdomain=None,
                 url_defaults=None, root_path=None):
        cli_commands = ((self.create_user, 'user create'),)
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)
        self.add_url_rule('/login', view_func=login, methods={'POST'})

    @argument('email')
    @option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_user(self, email: str, password: str) -> dict:
        """
        Creates an user.
        """
        with self.app.app_context():
            self.SCHEMA(only={'email', 'password'}, exclude=('token',)) \
                .load({'email': email, 'password': password})
            user = User(email=email, password=password)
            db.session.add(user)
            db.session.commit()
            return self.schema.dump(user)
