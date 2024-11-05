"""This command is used for up one snapshot."""

import json

# from uuid import uuid4
from io import BytesIO
from os import listdir
from os import remove as remove_file
from os.path import isfile, join
from pathlib import Path

import click
from flask.testing import FlaskClient
from flask_wtf.csrf import generate_csrf

from ereuse_devicehub.resources.user.models import User


class UploadSnapshots:
    """Command.

    This command allow upload all snapshots than exist
    in the directory snapshots_upload.
    If this snapshot exist replace it.

    """

    def __init__(self, app) -> None:
        """Init function."""
        super().__init__()
        self.app = app
        self.schema = app.config.get('DB_SCHEMA')
        self.app.cli.command('snapshot', short_help='Upload snapshots.')(self.run)

    @click.argument('email')
    @click.argument('password')
    def run(self, email, password=None):
        """Run command."""
        self.email = email
        self.password = password
        self.json_wb = None
        self.onlyfiles = []

        self.get_user()
        self.get_files()
        for f in self.onlyfiles:
            self.file_snapshot = f
            self.open_snapshot()
            self.build_snapshot()
        self.remove_files()

    def get_user(self):
        """Get datamodel of user."""
        self.user = User.query.filter_by(email=self.email).one()
        self.client = FlaskClient(self.app, use_cookies=True)
        self.client.get('/login/')

        data = {
            'email': self.email,
            'password': self.password,
            'remember': False,
            'csrf_token': generate_csrf(),
        }
        self.client.post('/login/', data=data, follow_redirects=True)

    def remove_files(self):
        """Open snapshot file."""
        for f in self.onlyfiles:
            remove_file(Path(__file__).parent.joinpath('snapshot_files').joinpath(f))

    def open_snapshot(self):
        """Open snapshot file."""
        with Path(__file__).parent.joinpath('snapshot_files').joinpath(
            self.file_snapshot,
        ).open() as file_snapshot:
            self.json_wb = json.loads(file_snapshot.read())
            b_snapshot = bytes(json.dumps(self.json_wb), 'utf-8')
            self.file_snap = (BytesIO(b_snapshot), self.file_snapshot)

    def build_snapshot(self):
        """Build the devices of snapshot."""
        uri = '/inventory/upload-snapshot/'

        if not self.json_wb:
            return

        self.client.get(uri)
        data = {
            'snapshot': self.file_snap,
            'csrf_token': generate_csrf(),
        }

        self.client.post(uri, data=data, content_type="multipart/form-data")

    def get_files(self):
        """Read snaoshot_files dir."""
        mypath = Path(__file__).parent.joinpath('snapshot_files')
        for f in listdir(mypath):
            if not isfile(join(mypath, f)):
                continue
            if not f[-5:] == ".json":
                continue
            self.onlyfiles.append(f)

    #     def save(self, commit=True, user_trusts=True):
    #     if any([x == 'Error' for x in self.result.values()]):
    #         return
    #     schema = SnapshotSchema()
    #     schema_lite = Snapshot_lite()
    #     devices = []
    #     self.tmp_snapshots = app.config['TMP_SNAPSHOTS']
    #     for filename, snapshot_json in self.snapshots:
    #         self.json_wb = copy.copy(snapshot_json)
    #         path_snapshot = save_json(snapshot_json, self.tmp_snapshots, g.user.email)
    #         debug = snapshot_json.pop('debug', None)
    #         self.version = snapshot_json.get('schema_api')
    #         self.uuid = snapshot_json.get('uuid')
    #         self.sid = snapshot_json.get('sid')

    #         if self.is_wb_lite_snapshot(self.version):
    #             self.snapshot_json = schema_lite.load(snapshot_json)
    #             snapshot_json = ParseSnapshotLsHw(self.snapshot_json).snapshot_json
    #         else:
    #             self.version = snapshot_json.get('version')
    #             system_uuid = self.get_uuid(debug)
    #             if system_uuid:
    #                 snapshot_json['device']['system_uuid'] = system_uuid
    #             self.get_fields_extra(debug, snapshot_json)

    #         try:
    #             snapshot_json = schema.load(snapshot_json)
    #             response = self.build(
    #                 snapshot_json, create_new_device=self.create_new_devices
    #             )
    #         except ValidationError as err:
    #             txt = "{}".format(err)
    #             self.errors(txt=txt)
    #             self.result[filename] = 'Error'
    #             continue

    #         if isinstance(response.device, Computer):
    #             response.device.user_trusts = user_trusts
    #         db.session.add(response)
    #         devices.append(response.device.binding.device)

    #         if hasattr(response, 'type'):
    #             self.result[filename] = 'Ok'
    #             self.errors(txt="Ok", severity=Severity.Info, snapshot=response)
    #         else:
    #             self.result[filename] = 'Error'

    #         move_json(self.tmp_snapshots, path_snapshot, g.user.email)

    #     if commit:
    #         db.session.commit()
    #     return self.result, devices
