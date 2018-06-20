from click import argument, option
from flask import current_app as app

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.models import Organization, User
from ereuse_devicehub.resources.user.schemas import User as UserS
from ereuse_devicehub.resources.user.views import UserView, login
from teal.db import SQLAlchemy
from teal.resource import Converters, Resource


class UserDef(Resource):
    SCHEMA = UserS
    VIEW = UserView
    ID_CONVERTER = Converters.uuid
    AUTH = True

    def __init__(self, app, import_name=__package__, static_folder=None,
                 static_url_path=None, template_folder=None, url_prefix=None, subdomain=None,
                 url_defaults=None, root_path=None):
        cli_commands = ((self.create_user, 'create-user'),)
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)
        self.add_url_rule('/login', view_func=login, methods={'POST'})

    @argument('email')
    @option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_user(self, email: str, password: str) -> dict:
        """
        Creates an user.
        """
        u = self.SCHEMA(only={'email', 'password'}, exclude=('token',)) \
            .load({'email': email, 'password': password})
        user = User(**u)
        db.session.add(user)
        db.session.commit()
        return self.schema.dump(user)


class OrganizationDef(Resource):
    __type__ = 'Organization'
    ID_CONVERTER = Converters.uuid
    AUTH = True

    def __init__(self, app, import_name=__package__, static_folder=None, static_url_path=None,
                 template_folder=None, url_prefix=None, subdomain=None, url_defaults=None,
                 root_path=None):
        cli_commands = ((self.create_org, 'create-org'),)
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)

    @argument('name')
    @argument('tax_id')
    @argument('country')
    def create_org(self, **kw: dict) -> dict:
        """
        Creates an organization.
        COUNTRY has to be 2 characters as defined by
        """
        org = Organization(**self.schema.load(kw))
        db.session.add(org)
        db.session.commit()
        return self.schema.dump(org)

    def init_db(self, db: SQLAlchemy):
        """Creates the default organization."""
        org = Organization(**app.config.get_namespace('ORGANIZATION_'))
        db.session.add(org)
