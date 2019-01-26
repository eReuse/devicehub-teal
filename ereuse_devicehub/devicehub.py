import uuid
from typing import Type

import boltons.urlutils
import click
import click_spinner
import ereuse_utils.cli
from ereuse_utils.session import DevicehubClient
from flask.globals import _app_ctx_stack, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from teal.teal import Teal

from ereuse_devicehub.auth import Auth
from ereuse_devicehub.client import Client
from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.db import db
from ereuse_devicehub.dummy.dummy import Dummy
from ereuse_devicehub.resources.device.search import DeviceSearch
from ereuse_devicehub.resources.inventory import Inventory, InventoryDef


class Devicehub(Teal):
    test_client_class = Client
    Dummy = Dummy

    def __init__(self,
                 inventory: str,
                 config: DevicehubConfig = DevicehubConfig(),
                 db: SQLAlchemy = db,
                 import_name=__name__.split('.')[0],
                 static_url_path=None,
                 static_folder='static',
                 static_host=None,
                 host_matching=False,
                 subdomain_matching=False,
                 template_folder='templates',
                 instance_path=None,
                 instance_relative_config=False,
                 root_path=None,
                 Auth: Type[Auth] = Auth):
        assert inventory
        super().__init__(config, db, inventory, import_name, static_url_path, static_folder,
                         static_host,
                         host_matching, subdomain_matching, template_folder, instance_path,
                         instance_relative_config, root_path, Auth)
        self.id = inventory
        """The Inventory ID of this instance. In Teal is the app.schema."""
        self.dummy = Dummy(self)
        self.before_request(self.register_db_events_listeners)
        self.cli.command('regenerate-search')(self.regenerate_search)
        self.cli.command('init-db')(self.init_db)
        self.before_request(self._prepare_request)

    def register_db_events_listeners(self):
        """Registers the SQLAlchemy event listeners."""
        # todo can I make it with a global Session only?
        event.listen(db.session, 'before_commit', DeviceSearch.update_modified_devices)

    # noinspection PyMethodOverriding
    @click.option('--name', '-n',
                  default='Test 1',
                  help='The human name of the inventory.')
    @click.option('--org-name', '-on',
                  default='My Organization',
                  help='The name of the default organization that owns this inventory.')
    @click.option('--org-id', '-oi',
                  default='foo-bar',
                  help='The Tax ID of the organization.')
    @click.option('--tag-url', '-tu',
                  type=ereuse_utils.cli.URL(scheme=True, host=True, path=False),
                  default='http://example.com',
                  help='The base url (scheme and host) of the tag provider.')
    @click.option('--tag-token', '-tt',
                  type=click.UUID,
                  default='899c794e-1737-4cea-9232-fdc507ab7106',
                  help='The token provided by the tag provider. It is an UUID.')
    @click.option('--erase/--no-erase',
                  default=False,
                  help='Delete the full database before? Including all schemas and users.')
    @click.option('--common/--no-common',
                  default=False,
                  help='Creates common databases. Only execute if the database is empty.')
    def init_db(self, name: str,
                org_name: str,
                org_id: str,
                tag_url: boltons.urlutils.URL,
                tag_token: uuid.UUID,
                erase: bool,
                common: bool):
        """Initializes this inventory with the provided configurations."""
        assert _app_ctx_stack.top, 'Use an app context.'
        print('Initializing database...'.ljust(30), end='')
        with click_spinner.spinner():
            if erase:
                self.db.drop_all()
            exclude_schema = 'common' if not common else None
            self._init_db(exclude_schema=exclude_schema)
            InventoryDef.set_inventory_config(name, org_name, org_id, tag_url, tag_token)
            DeviceSearch.set_all_devices_tokens_if_empty(self.db.session)
            self._init_resources(exclude_schema=exclude_schema)
            self.db.session.commit()
        print('done.')

    def regenerate_search(self):
        """Re-creates from 0 all the search tables."""
        DeviceSearch.regenerate_search_table(self.db.session)
        db.session.commit()
        print('Done.')

    def _prepare_request(self):
        """Prepares request stuff."""
        inv = g.inventory = Inventory.current  # type: Inventory
        g.tag_provider = DevicehubClient(base_url=inv.tag_provider,
                                         token=DevicehubClient.encode_token(inv.tag_token))
