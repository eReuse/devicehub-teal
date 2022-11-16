import json
from binascii import Error as asciiError

from flask import Blueprint
from flask import current_app as app
from flask import g, jsonify, request
from flask.views import View
from flask.wrappers import Response
from marshmallow.exceptions import ValidationError
from werkzeug.exceptions import Unauthorized

from ereuse_devicehub.auth import Auth
from ereuse_devicehub.db import db
from ereuse_devicehub.parser.models import SnapshotsLog
from ereuse_devicehub.parser.parser import ParseSnapshotLsHw
from ereuse_devicehub.parser.schemas import Snapshot_lite
from ereuse_devicehub.resources.action.views.snapshot import (
    SnapshotMixin,
    move_json,
    save_json,
)
from ereuse_devicehub.resources.enums import Severity

api = Blueprint('api', __name__, url_prefix='/api')


class LoginMixin(View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.authenticate()

    def authenticate(self):
        unauthorized = Unauthorized('Provide a suitable token.')
        basic_token = request.headers.get('Authorization', " ").split(" ")
        if not len(basic_token) == 2:
            raise unauthorized

        token = basic_token[1]
        try:
            token = Auth.decode(token)
        except asciiError:
            raise unauthorized
        self.user = Auth().authenticate(token)
        g.user = self.user


class InventoryView(LoginMixin, SnapshotMixin):
    methods = ['POST']

    def dispatch_request(self):
        snapshot_json = json.loads(request.data)
        self.tmp_snapshots = app.config['TMP_SNAPSHOTS']
        self.path_snapshot = save_json(snapshot_json, self.tmp_snapshots, g.user.email)
        snapshot_json = self.validate(snapshot_json)
        if type(snapshot_json) == Response:
            return snapshot_json

        self.snapshot_json = ParseSnapshotLsHw(snapshot_json).get_snapshot()

        snapshot = self.build()
        snapshot.device.set_hid()
        snapshot.device.binding.device.set_hid()
        db.session.add(snapshot)

        snap_log = SnapshotsLog(
            description='Ok',
            snapshot_uuid=snapshot.uuid,
            severity=Severity.Info,
            sid=snapshot.sid,
            version=str(snapshot.version),
            snapshot=snapshot,
        )
        snap_log.save()

        db.session().final_flush()
        db.session.commit()
        url = "https://{}/".format(app.config['HOST'])
        public_url = "{}{}".format(url.strip("/"), snapshot.device.url.to_text())
        self.response = jsonify(
            {
                'dhid': snapshot.device.dhid,
                'url': url,
                'public_url': public_url,
            }
        )
        self.response.status_code = 201
        move_json(self.tmp_snapshots, self.path_snapshot, g.user.email)
        return self.response

    def validate(self, snapshot_json):
        self.schema = Snapshot_lite()
        try:
            return self.schema.load(snapshot_json)
        except ValidationError as err:
            txt = "{}".format(err)
            uuid = snapshot_json.get('uuid')
            sid = snapshot_json.get('sid')
            version = snapshot_json.get('version')
            error = SnapshotsLog(
                description=txt,
                snapshot_uuid=uuid,
                severity=Severity.Error,
                sid=sid,
                version=str(version),
            )
            error.save(commit=True)
            # raise err
            self.response = jsonify(err)
            self.response.status_code = 400
            return self.response


api.add_url_rule('/inventory/', view_func=InventoryView.as_view('inventory'))
