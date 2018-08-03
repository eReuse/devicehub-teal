import click
from flask import current_app as app

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent import models, schemas
from teal.db import SQLAlchemy
from teal.resource import Converters, Resource


class AgentDef(Resource):
    SCHEMA = schemas.Agent
    VIEW = None
    AUTH = True
    ID_CONVERTER = Converters.uuid


class OrganizationDef(AgentDef):
    SCHEMA = schemas.Organization
    VIEW = None

    def __init__(self, app, import_name=__package__, static_folder=None, static_url_path=None,
                 template_folder=None, url_prefix=None, subdomain=None, url_defaults=None,
                 root_path=None):
        cli_commands = ((self.create_org, 'create-org'),)
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)

    @click.argument('name')
    @click.argument('tax_id')
    @click.argument('country')
    def create_org(self, name: str, tax_id: str = None, country: str = None) -> dict:
        """Creates an organization."""
        org = models.Organization(**self.schema.load(
            {
                'name': name,
                'taxId': tax_id,
                'country': country
            }
        ))
        db.session.add(org)
        db.session.commit()
        return self.schema.dump(org)

    def init_db(self, db: SQLAlchemy):
        """Creates the default organization."""
        org = models.Organization(**app.config.get_namespace('ORGANIZATION_'))
        db.session.add(org)


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
