from typing import List
from uuid import UUID

import click.testing
import pytest
from boltons.urlutils import URL

import ereuse_devicehub.cli
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.agent.models import Organization
from ereuse_devicehub.resources.inventory import Inventory
from ereuse_devicehub.resources.user import User
from tests.conftest import TestConfig

"""Tests the management of inventories in a multi-inventory environment
(several Devicehub instances that point at different schemas).
"""


class NoExcCliRunner(click.testing.CliRunner):
    """Runner that interfaces with the Devicehub CLI."""

    def invoke(
        self, *args, input=None, env=None, catch_exceptions=False, color=False, **extra
    ):
        r = super().invoke(
            ereuse_devicehub.cli.cli, args, input, env, catch_exceptions, color, **extra
        )
        assert r.exit_code == 0, 'CLI code {}: {}'.format(r.exit_code, r.output)
        return r

    def inv(self, name: str):
        """Set an inventory as an environment variable."""
        self.env = {'dhi': name}


@pytest.fixture()
def cli(config, _app):
    """Returns an interface for the dh CLI client,
    cleaning the database afterwards.
    """

    def drop_schemas():
        with _app.app_context():
            _app.db.drop_schema(schema='tdb1')
            _app.db.drop_schema(schema='tdb2')
            _app.db.drop_schema(schema='common')

    drop_schemas()
    ereuse_devicehub.cli.DevicehubGroup.CONFIG = TestConfig
    yield NoExcCliRunner()
    drop_schemas()


@pytest.fixture()
def tdb1(config):
    return Devicehub(inventory='tdb1', config=config, db=db)


@pytest.fixture()
def tdb2(config):
    return Devicehub(inventory='tdb2', config=config, db=db)


@pytest.mark.mvp
def test_inventory_create_delete_user(cli, tdb1, tdb2):
    """Tests creating two inventories with users, one user has
    access to the first inventory and the other to both. Finally, deletes
    the first inventory, deleting only the first user too.
    """
    # Create first DB
    cli.inv('tdb1')
    cli.invoke(
        'inv',
        'add',
        '-n',
        'Test DB1',
        '-on',
        'ACME DB1',
        '-oi',
        'acme-id',
        '-tu',
        'https://example.com',
        '-tt',
        '3c66a6ad-22de-4db6-ac46-d8982522ec40',
        '--common',
    )

    # Create an user for first DB
    cli.invoke(
        'user', 'add', 'foo@foo.com', '-a', 'Foo', '-c', 'ES', '-p', 'Such password'
    )

    with tdb1.app_context():
        # There is a row for the inventory
        inv = Inventory.query.one()  # type: Inventory
        assert inv.id == 'tdb1'
        assert inv.name == 'Test DB1'
        assert inv.tag_provider == URL('https://example.com')
        assert inv.tag_token == UUID('3c66a6ad-22de-4db6-ac46-d8982522ec40')
        assert db.has_schema('tdb1')
        org = Organization.query.one()  # type: Organization
        # assert inv.org_id == org.id
        assert org.name == 'ACME DB1'
        assert org.tax_id == 'acme-id'
        user = User.query.one()  # type: User
        assert user.email == 'foo@foo.com'

    cli.inv('tdb2')
    # Create a second DB
    # Note how we don't create common anymore
    cli.invoke(
        'inv',
        'add',
        '-n',
        'Test DB2',
        '-on',
        'ACME DB2',
        '-oi',
        'acme-id-2',
        '-tu',
        'https://example.com',
        '-tt',
        'fbad1c08-ffdc-4a61-be49-464962c186a8',
    )
    # Create an user for with access for both DB
    cli.invoke('user', 'add', 'bar@bar.com', '-a', 'Bar', '-p', 'Wow password')

    with tdb2.app_context():
        inventories = Inventory.query.all()  # type: List[Inventory]
        assert len(inventories) == 2
        assert inventories[0].id == 'tdb1'
        assert inventories[1].id == 'tdb2'
        assert db.has_schema('tdb2')
        org_db2 = Organization.query.one()
        assert org_db2 != org
        assert org_db2.name == 'ACME DB2'
        users = User.query.all()  # type: List[User]
        assert users[0].email == 'foo@foo.com'
        assert users[1].email == 'bar@bar.com'

    # Delete tdb1
    cli.inv('tdb1')
    cli.invoke('inv', 'del', '--yes')

    with tdb2.app_context():
        # There is only tdb2 as inventory
        inv = Inventory.query.one()  # type: Inventory
        assert inv.id == 'tdb2'
        # User foo@foo.com is deleted because it only
        # existed in tdb1, but not bar@bar.com which existed
        # in another inventory too (tdb2)
        user = User.query.one()  # type: User
        assert user.email == 'bar@bar.com'
        assert not db.has_schema('tdb1')
        assert db.has_schema('tdb2')


@pytest.mark.mvp
def test_create_existing_inventory(cli, tdb1):
    """Tries to create twice the same inventory."""
    cli.inv('tdb1')
    cli.invoke('inv', 'add', '--common')
    with tdb1.app_context():
        assert db.has_schema('tdb1')
    with pytest.raises(AssertionError):
        cli.invoke('inv', 'add', '--common')
        pytest.fail('Schema tdb1 already exists.')
