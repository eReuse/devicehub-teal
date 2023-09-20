import os
import uuid
from typing import Type

import boltons.urlutils
import click
import click_spinner
from flask import _app_ctx_stack, g
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy

import ereuse_devicehub.ereuse_utils.cli
from ereuse_devicehub.auth import Auth
from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.commands.adduser import AddUser
from ereuse_devicehub.commands.check_install import CheckInstall
from ereuse_devicehub.commands.initdatas import InitDatas
from ereuse_devicehub.commands.snapshots import UploadSnapshots

# from ereuse_devicehub.commands.reports import Report
from ereuse_devicehub.commands.users import GetToken
from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.db import db
from ereuse_devicehub.dummy.dummy import Dummy
from ereuse_devicehub.ereuse_utils.session import DevicehubClient
from ereuse_devicehub.resources.device.search import DeviceSearch
from ereuse_devicehub.resources.inventory import Inventory, InventoryDef
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.teal.db import ResourceNotFound, SchemaSQLAlchemy
from ereuse_devicehub.teal.teal import Teal
from ereuse_devicehub.templating import Environment

try:
    from ereuse_devicehub.modules.oidc.commands.sync_dlt import GetMembers
except Exception:
    GetMembers = None

try:
    from ereuse_devicehub.modules.dpp.commands.register_user_dlt import RegisterUserDlt
except Exception:
    RegisterUserDlt = None

try:
    from ereuse_devicehub.modules.oidc.commands.add_member import AddMember
except Exception:
    AddMember = None

try:
    from ereuse_devicehub.modules.oidc.commands.client_member import AddClientOidc
except Exception:
    AddClientOidc = None

try:
    from ereuse_devicehub.modules.oidc.commands.insert_member_in_dlt import InsertMember
except Exception:
    InsertMembe = None

try:
    from ereuse_devicehub.modules.oidc.commands.add_contract_oidc import AddContractOidc
except Exception:
    AddContractOidc = None


class Devicehub(Teal):
    test_client_class = Client
    Dummy = Dummy
    # Report = Report
    jinja_environment = Environment

    def __init__(
        self,
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
        Auth: Type[Auth] = Auth,
    ):
        assert inventory
        super().__init__(
            config,
            db,
            inventory,
            import_name,
            static_url_path,
            static_folder,
            static_host,
            host_matching,
            subdomain_matching,
            template_folder,
            instance_path,
            instance_relative_config,
            root_path,
            False,
            Auth,
        )
        self.id = inventory
        """The Inventory ID of this instance. In Teal is the app.schema."""
        self.dummy = Dummy(self)
        # self.report = Report(self)
        self.get_token = GetToken(self)
        self.initdata = InitDatas(self)
        self.adduser = AddUser(self)
        self.uploadsnapshots = UploadSnapshots(self)
        self.checkinstall = CheckInstall(self)

        if GetMembers:
            self.get_members = GetMembers(self)
        if RegisterUserDlt:
            self.dlt_register_user = RegisterUserDlt(self)
        if AddMember:
            self.dlt_insert_members = AddMember(self)
        if AddClientOidc:
            self.add_client_oidc = AddClientOidc(self)
        if InsertMember:
            self.dlt_insert_members = InsertMember(self)

        if AddContractOidc:
            self.add_contract_oidc = AddContractOidc(self)

        @self.cli.group(
            short_help='Inventory management.',
            help='Manages the inventory {}.'.format(os.environ.get('dhi')),
        )
        def inv():
            pass

        inv.command('add')(self.init_db)
        inv.command('del')(self.delete_inventory)
        inv.command('search')(self.regenerate_search)
        self.before_request(self._prepare_request)

        self.configure_extensions()

    def configure_extensions(self):
        # configure Flask-Login
        login_manager = LoginManager()
        login_manager.init_app(self)
        login_manager.login_view = "core.login"

        @login_manager.user_loader
        def load_user(user_id):
            # TODO(@slamora) refactor when teal library has been drop.
            # `load_user` expects None if the user ID is invalid or the
            # session has expired so we need to handle Exception raised
            # by teal (it's overriding default behaviour of flask-sqlalchemy
            # which already returns None)
            try:
                return User.query.get(user_id)
            except ResourceNotFound:
                return None

    # noinspection PyMethodOverriding
    @click.option(
        '--name', '-n', default='Test 1', help='The human name of the inventory.'
    )
    @click.option(
        '--org-name',
        '-on',
        default='My Organization',
        help='The name of the default organization that owns this inventory.',
    )
    @click.option(
        '--org-id', '-oi', default='foo-bar', help='The Tax ID of the organization.'
    )
    @click.option(
        '--tag-url',
        '-tu',
        type=ereuse_devicehub.ereuse_utils.cli.URL(scheme=True, host=True, path=False),
        default='http://example.com',
        help='The base url (scheme and host) of the tag provider.',
    )
    @click.option(
        '--tag-token',
        '-tt',
        type=click.UUID,
        default='899c794e-1737-4cea-9232-fdc507ab7106',
        help='The token provided by the tag provider. It is an UUID.',
    )
    @click.option(
        '--erase/--no-erase',
        default=False,
        help='Delete the schema before? '
        'If --common is set this includes the common database.',
    )
    @click.option(
        '--common/--no-common',
        default=False,
        help='Creates common databases. Only execute if the database is empty.',
    )
    def init_db(
        self,
        name: str,
        org_name: str,
        org_id: str,
        tag_url: boltons.urlutils.URL,
        tag_token: uuid.UUID,
        erase: bool,
        common: bool,
    ):
        """Creates an inventory.

        This creates the database and adds the inventory to the
        inventory tables with the passed-in settings, and does nothing if the
        inventory already exists.

        After you create the inventory you might want to create an user
        executing *dh user add*.
        """
        assert _app_ctx_stack.top, 'Use an app context.'
        print('Initializing database...'.ljust(30), end='')
        with click_spinner.spinner():
            if erase:
                self.db.drop_all(common_schema=common)
            assert not db.has_schema(self.id), 'Schema {} already exists.'.format(
                self.id
            )
            exclude_schema = 'common' if not common else None
            self._init_db(exclude_schema=exclude_schema)
            InventoryDef.set_inventory_config(
                name, org_name, org_id, tag_url, tag_token
            )
            DeviceSearch.set_all_devices_tokens_if_empty(self.db.session)
            self._init_resources(exclude_schema=exclude_schema)
            self.db.session.commit()
        print('done.')

    def _init_db(self, exclude_schema=None) -> bool:
        if exclude_schema:
            assert isinstance(self.db, SchemaSQLAlchemy)
            self.db.create_all(exclude_schema=exclude_schema)
        else:
            self.db.create_all()

        return True

    @click.confirmation_option(
        prompt='Are you sure you want to delete the inventory {}?'.format(
            os.environ.get('dhi')
        )
    )
    def delete_inventory(self):
        """Erases an inventory.

        This removes its private database and its entry in the common
        inventory.

        This deletes users that have only access to this inventory.
        """
        InventoryDef.delete_inventory()
        self.db.session.commit()
        self.db.drop_all(common_schema=False)

    def regenerate_search(self):
        """Re-creates from 0 all the search tables."""
        DeviceSearch.regenerate_search_table(self.db.session)
        db.session.commit()
        print('Done.')

    def _prepare_request(self):
        """Prepares request stuff."""
        inv = g.inventory = Inventory.current  # type: Inventory
        g.tag_provider = DevicehubClient(
            base_url=inv.tag_provider, token=DevicehubClient.encode_token(inv.tag_token)
        )
        # NOTE: models init methods expects that current user is
        #   available on g.user (e.g. to initialize object owner)
        g.user = current_user

    def create_client(self, email='user@dhub.com', password='1234'):
        client = UserClient(self, email, password, response_wrapper=self.response_class)
        client.login()
        return client
