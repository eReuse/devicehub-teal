"""This command is used for up one snapshot."""

import json

import click

from ereuse_devicehub.resources.action.models import Snapshot
from ereuse_devicehub.resources.user.models import User


class CheckInstall:
    """Command.

    This command check if the installation was ok and the
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
        self.OKGREEN = '\033[92m'
        # self.WARNING = '\033[93m'
        self.FAIL = '\033[91m'
        self.ENDC = '\033[0m'
        print("\n")
        try:
            self.check_user()
            self.check_snapshot()
        except Exception:
            txt = "There was an Error in the installation!"
            print("\n" + self.FAIL + txt + self.ENDC)
            return

        txt = "The installation is OK!"
        print("\n" + self.OKGREEN + txt + self.ENDC)

    def check_user(self):
        """Get datamodel of user."""
        self.user = User.query.filter_by(email=self.email).first()

        txt = "Register user to the DLT       "
        try:
            assert self.user.api_keys_dlt is not None
            token_dlt = self.user.get_dlt_keys(self.password)
            assert token_dlt.get('data', {}).get('eth_pub_key') is not None
        except Exception:
            self.print_fail(txt)
            raise (txt)

        self.print_ok(txt)

        api_token = token_dlt.get('data', {}).get('api_token')

        txt = "Register user roles in the DLT "
        try:
            rols = self.user.get_rols(api_token)
            assert self.user.rols_dlt is not None
            assert self.user.rols_dlt != []
            assert self.user.rols_dlt == json.dumps([x for x, y in rols])
        except Exception:
            self.print_fail(txt)
            raise (txt)

        self.print_ok(txt)

    def check_snapshot(self):
        self.snapshot = Snapshot.query.filter_by(author=self.user).first()
        if not self.snapshot:
            txt = "Impossible register snapshot   "
            self.print_fail(txt)
            raise (txt)

        self.device = self.snapshot.device

        txt = "Generate DPP                   "
        try:
            assert self.device.chid is not None
            assert self.snapshot.json_wb is not None
            assert self.snapshot.phid_dpp is not None
        except Exception:
            self.print_fail(txt)
            raise (txt)

        self.print_ok(txt)

        txt = "Register DPP in the DLT        "
        try:
            assert len(self.device.dpps) > 0
            dpp = self.device.dpps[0]
            assert type(dpp.timestamp) == int
            assert dpp in self.snapshot.dpp
            assert dpp.documentId == str(self.snapshot.uuid)
            # if 'Device already exists' in DLT before
            #   device.proofs == 0
            #   Snapshot.proof == 1 [erase]

            # if Device is new in DLT before
            #   device.proofs == 1
            #   Snapshot.proof == 1 or 2 [Register, erase]

            assert len(self.device.proofs) in [0, 1]
            assert len(self.snapshot.proofs) in [0, 1, 2]
        except Exception:
            self.print_fail(txt)
            raise (txt)

        self.print_ok(txt)

    def print_ok(self, msg):
        print(msg + self.OKGREEN + " OK!" + self.ENDC)

    def print_fail(self, msg):
        print(msg + self.FAIL + " FAIL!" + self.ENDC)
