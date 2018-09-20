from click import argument, option
from flask import current_app
from teal.resource import Converters, Resource

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user import schemas
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.user.views import UserView, login


class UserDef(Resource):
    SCHEMA = schemas.User
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
    @option('-a', '--agent', help='The name of an agent to create with the user.')
    @option('-c', '--country', help='The country of the agent (if --agent is set).')
    @option('-t', '--telephone', help='The telephone of the agent (if --agent is set).')
    @option('-t', '--tax-id', help='The tax id of the agent (if --agent is set).')
    @option('-p', '--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_user(self, email: str, password: str, agent: str = None, country: str = None,
                    telephone: str = None, tax_id: str = None) -> dict:
        """Creates an user.

        If ``--agent`` is passed, it creates an ``Individual`` agent
        that represents the user.
        """
        from ereuse_devicehub.resources.agent.models import Individual
        u = self.SCHEMA(only={'email', 'password'}, exclude=('token',)) \
            .load({'email': email, 'password': password})
        user = User(**u)
        agent = Individual(**current_app.resources[Individual.t].schema.load(
            dict(name=agent, email=email, country=country, telephone=telephone, taxId=tax_id)
        ))
        user.individuals.add(agent)
        db.session.add(user)
        db.session.commit()
        return self.schema.dump(user)
