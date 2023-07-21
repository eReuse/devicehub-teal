"""This command is used for up one snapshot."""

import copy
import json
from io import BytesIO

# from uuid import uuid4
from pathlib import Path

import click
from decouple import config
from flask import Session, g

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.schemas import Snapshot as SnapshotSchema
from ereuse_devicehub.resources.action.views.snapshot import SnapshotMixin
from ereuse_devicehub.resources.device.models import Computer
from ereuse_devicehub.resources.user.models import User


class UploadSnapshots(SnapshotMixin):
    """
    Command.

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
        self.schema = SnapshotSchema()

        with self.app.app_context():
            self.get_user()
            self.open_snapshot()
            self.load_schema()
            self.build_snapshot()
            # db.session.commit()

    def get_user(self):
        """Get datamodel of user."""
        self.email = config('EMAIL_DEMO')
        self.password = config('PASSWORD_DEMO')
        self.user = User.query.filter_by(email=self.email).one()
        import pdb

        pdb.set_trace()
        g.user = self.user
        # if 'dpp' in self.app.blueprints.keys():
        #    client = UserClient(
        #        self.app,
        #        self.email,
        #        self.password,
        #        response_wrapper=self.app.response_class
        #    )
        #    client.login_web(self.email, self.password)

        from flask.testing import FlaskClient
        from flask_wtf.csrf import generate_csrf

        client = FlaskClient(self.app, use_cookies=True)

        body, status, headers = client.get('/login/')

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
            self.file_snapshot
        ).open() as file_snapshot:
            self.json_wb = json.loads(file_snapshot.read())
            b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
            self.file_snap = (BytesIO(b_snapshot), self.file_snapshot)

    def load_schema(self):
        """Load schema for check snapshot."""
        if not self.json_wb:
            return
        self.snapshot_json = self.schema.load(self.json_wb)

    def build_snapshot(self):
        """Build the devices of snapshot."""
        import pdb

        pdb.set_trace()
        if not self.snapshot_json:
            return
        response = self.build(self.snapshot_json)
        if isinstance(response.device, Computer):
            response.device.user_trusts = True
            db.session.add(response)

    uri = '/inventory/upload-snapshot/'
    snapshot = conftest.yaml2json(file_name.split(".json")[0])
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)
    user.get(uri)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user.post(uri, data=data, content_type="multipart/form-data")

    return Snapshot.query.one()
