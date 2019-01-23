import uuid

import boltons.urlutils
import click
import ereuse_utils.cli
from flask import current_app
from teal.db import ResourceNotFound
from teal.resource import Resource

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.inventory import schema
from ereuse_devicehub.resources.inventory.model import Inventory


class InventoryDef(Resource):
    SCHEMA = schema.Inventory
    VIEW = None

    def __init__(self, app, import_name=__name__.split('.')[0], static_folder=None,
                 static_url_path=None,
                 template_folder=None, url_prefix=None, subdomain=None, url_defaults=None,
                 root_path=None):
        cli_commands = (
            (self.set_inventory_config_cli, 'set-inventory-config'),
        )
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)

    @click.option('--name', '-n',
                  default='Test 1',
                  help='The human name of the inventory.')
    @click.option('--org-name', '-on',
                  default=None,
                  help='The name of the default organization that owns this inventory.')
    @click.option('--org-id', '-oi',
                  default=None,
                  help='The Tax ID of the organization.')
    @click.option('--tag-url', '-tu',
                  type=ereuse_utils.cli.URL(scheme=True, host=True, path=False),
                  default=None,
                  help='The base url (scheme and host) of the tag provider.')
    @click.option('--tag-token', '-tt',
                  type=click.UUID,
                  default=None,
                  help='The token provided by the tag provider. It is an UUID.')
    def set_inventory_config_cli(self, **kwargs):
        """Sets the inventory configuration. Only updates passed-in
        values.
        """
        self.set_inventory_config(**kwargs)
        db.session.commit()

    @classmethod
    def set_inventory_config(cls,
                             name: str = None,
                             org_name: str = None,
                             org_id: str = None,
                             tag_url: boltons.urlutils.URL = None,
                             tag_token: uuid.UUID = None):
        try:
            inventory = Inventory.current
        except ResourceNotFound:  # No inventory defined in db yet
            inventory = Inventory(id=current_app.id,
                                  name=name,
                                  tag_provider=tag_url,
                                  tag_token=tag_token)
            db.session.add(inventory)
        if org_name or org_id:
            from ereuse_devicehub.resources.agent.models import Organization
            try:
                org = Organization.query.filter_by(tax_id=org_id, name=org_name).one()
            except ResourceNotFound:
                org = Organization(tax_id=org_id, name=org_name)
            org.default_of = inventory
            db.session.add(org)
        if tag_url:
            inventory.tag_provider = tag_url
        if tag_token:
            inventory.tag_token = tag_token
