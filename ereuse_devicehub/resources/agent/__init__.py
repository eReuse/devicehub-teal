import json

import click
from boltons.typeutils import classproperty

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent import models, schemas
from ereuse_devicehub.teal.resource import Converters, Resource


class AgentDef(Resource):
    SCHEMA = schemas.Agent
    VIEW = None
    AUTH = True
    ID_CONVERTER = Converters.uuid


class OrganizationDef(AgentDef):
    SCHEMA = schemas.Organization
    VIEW = None

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
        cli_commands = ((self.create_org, 'add'),)
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

    @click.argument('name')
    @click.option('--tax_id', '-t')
    @click.option('--country', '-c')
    def create_org(self, name: str, tax_id: str = None, country: str = None) -> dict:
        """Creates an organization."""
        org = models.Organization(
            **self.schema.load({'name': name, 'taxId': tax_id, 'country': country})
        )
        db.session.add(org)
        db.session.commit()
        o = self.schema.dump(org)
        print(json.dumps(o, indent=2))
        return o

    @classproperty
    def cli_name(cls):
        return 'org'


class Membership(Resource):
    SCHEMA = schemas.Membership
    VIEW = None
    ID_CONVERTER = Converters.string


class IndividualDef(AgentDef):
    SCHEMA = schemas.Individual
    VIEW = None


class PersonDef(IndividualDef):
    SCHEMA = schemas.Person
    VIEW = None


class SystemDef(IndividualDef):
    SCHEMA = schemas.System
    VIEW = None
