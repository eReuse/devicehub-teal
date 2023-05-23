from typing import Iterable

from click import argument, option
from flask import current_app

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user import schemas
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.user.views import UserView, login, logout
from ereuse_devicehub.teal.resource import Converters, Resource


class UserDef(Resource):
    SCHEMA = schemas.User
    VIEW = UserView
    ID_CONVERTER = Converters.uuid
    AUTH = True

    def __init__(
        self,
        app,
        import_name=__name__.split('.')[0],
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
    ):
        cli_commands = ((self.create_user, 'add'),)
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )
        self.add_url_rule('/login/', view_func=login, methods={'POST'})
        logout_view = app.auth.requires_auth(logout)
        self.add_url_rule('/logout/', view_func=logout_view, methods={'GET'})

    @argument('email')
    @option(
        '-i',
        '--inventory',
        multiple=True,
        help='Inventories user has access to. By default this one.',
    )
    @option(
        '-a',
        '--agent',
        help='Create too an Individual agent representing this user, '
        'and give a name to this individual.',
    )
    @option('-c', '--country', help='The country of the agent (if --agent is set).')
    @option('-t', '--telephone', help='The telephone of the agent (if --agent is set).')
    @option('-t', '--tax-id', help='The tax id of the agent (if --agent is set).')
    @option('-p', '--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_user(
        self,
        email: str,
        password: str,
        inventory: Iterable[str] = tuple(),
        agent: str = None,
        country: str = None,
        telephone: str = None,
        tax_id: str = None,
    ) -> dict:
        """Create an user.

        If ``--agent`` is passed, it creates too an ``Individual``
        agent that represents the user.
        """
        from ereuse_devicehub.resources.agent.models import Individual

        u = self.SCHEMA(only={'email', 'password'}, exclude=('token',)).load(
            {'email': email, 'password': password}
        )
        if inventory:
            from ereuse_devicehub.resources.inventory import Inventory

            inventory = Inventory.query.filter(Inventory.id.in_(inventory))
        user = User(**u, inventories=inventory)
        agent = Individual(
            **current_app.resources[Individual.t].schema.load(
                dict(
                    name=agent,
                    email=email,
                    country=country,
                    telephone=telephone,
                    taxId=tax_id,
                )
            )
        )
        user.individuals.add(agent)
        db.session.add(user)
        db.session.commit()
        return self.schema.dump(user)
