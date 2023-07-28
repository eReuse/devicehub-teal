"""This command is used for up one snapshot."""

import json

import click

from ereuse_devicehub.resources.action.models import Snapshot
from ereuse_devicehub.resources.user.models import User


class CheckInstall:
    """Command.

    This command check if the instalation was ok and the
    integration with the api of DLT was ok too.

    """

    def __init__(self, app) -> None:
        """Init function."""
        super().__init__()
        self.app = app
        self.schema = app.config.get('DB_SCHEMA')
        self.app.cli.command('check_install', short_help='Upload snapshots.')(self.run)

    @click.argument('email')
    @click.argument('password')
    def run(self, email, password):
        """Run command."""

        self.email = email
        self.password = password
        OKGREEN = '\033[92m'
        # WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        try:
            self.check_user()
            self.check_snapshot()
        except Exception:
            print("\n" + FAIL + "There was an Error in the instalation!" + ENDC)
            return
        print("\n" + OKGREEN + "The instalation is OK!" + ENDC)

    def check_user(self):
        """Get datamodel of user."""
        self.user = User.query.filter_by(email=self.email).first()
        assert self.user.api_keys_dlt is not None
        token_dlt = self.user.get_dlt_keys(self.password)
        assert token_dlt.get('data', {}).get('eth_pub_key') is not None
        api_token = token_dlt.get('data', {}).get('api_token')
        rols = self.user.get_rols(api_token)
        assert self.user.rols_dlt is not None
        assert self.user.rols_dlt != []
        assert self.user.rols_dlt == json.dumps([x for x, y in rols])

    def check_snapshot(self):
        # import pdb

        # pdb.set_trace()
        self.snapshot = Snapshot.query.filter_by(author=self.user).first()
        self.device = self.snapshot.device
        assert self.snapshot.json_wb is not None
        assert len(self.device.dpps) == 1
        assert len(self.device.proofs) == 1
        assert self.device.chid is not None
        assert self.snapshot.phid_dpp is not None
        assert len(self.snapshot.dpp) == 1
        assert len(self.snapshot.proofs) == 2
