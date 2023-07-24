"""This command is used for up one snapshot."""

import json

# from uuid import uuid4
from io import BytesIO
from pathlib import Path

import click
from decouple import config
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

    @click.argument('file_snapshot')
    def run(self, file_snapshot):
        """Run command."""
        self.file_snapshot = file_snapshot
        self.snapshot_json = None
        self.json_wb = None

        with self.app.app_context():
            self.get_user()
            self.open_snapshot()
            self.build_snapshot()

    def get_user(self):
        """Get datamodel of user."""
        self.email = config('EMAIL_DEMO')
        self.password = config('PASSWORD_DEMO')
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

        if not self.snapshot_json:
            return

        self.client.get(uri)
        data = {
            'snapshot': self.file_snap,
            'csrf_token': generate_csrf(),
        }
        self.client.post(uri, data=data, content_type="multipart/form-data")
