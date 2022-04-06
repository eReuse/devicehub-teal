import json
from binascii import Error as asciiError

from flask import Blueprint
from flask import current_app as app
from flask import g, jsonify, request
from flask.views import View
from marshmallow import ValidationError
from sqlalchemy.util import OrderedSet
from werkzeug.exceptions import Unauthorized

from ereuse_devicehub.auth import Auth
from ereuse_devicehub.db import db
from ereuse_devicehub.parser.models import SnapshotErrors
from ereuse_devicehub.parser.parser import ParseSnapshotLsHw
from ereuse_devicehub.parser.schemas import Snapshot_lite
from ereuse_devicehub.resources.action.models import Snapshot
from ereuse_devicehub.resources.action.views.snapshot import move_json, save_json
from ereuse_devicehub.resources.device.models import Computer
from ereuse_devicehub.resources.enums import Severity, SnapshotSoftware
from ereuse_devicehub.resources.user.exceptions import InsufficientPermission

api = Blueprint('api', __name__, url_prefix='/api')


class LoginMix(View):
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


class InventoryView(LoginMix):
    methods = ['POST']

    def dispatch_request(self):
        import pdb

        pdb.set_trace()
        snapshot_json = json.loads(request.data)
        self.tmp_snapshots = app.config['TMP_SNAPSHOTS']
        self.path_snapshot = save_json(snapshot_json, self.tmp_snapshots, g.user.email)
        schema = Snapshot_lite()
        try:
            snapshot_json = schema.load(snapshot_json)
        except ValidationError as err:
            txt = "{}".format(err)
            uuid = snapshot_json.get('uuid')
            error = SnapshotErrors(
                description=txt, snapshot_uuid=uuid, severity=Severity.Error
            )
            error.save(commit=True)
            raise err
        self.snapshot_json = ParseSnapshotLsHw(snapshot_json)
        snapshot = self.build()
        ret = schema.jsonify(snapshot)  # transform it back
        ret.status_code = 201
        db.session.commit()
        return ret
        move_json(self.tmp_snapshots, self.path_snapshot, g.user.email)
        return jsonify("Ok")

    def build(self):
        device = self.snapshot_json.pop('device')  # type: Computer
        components = None
        if self.snapshot_json['software'] == (
            SnapshotSoftware.Workbench or SnapshotSoftware.WorkbenchAndroid
        ):
            components = self.snapshot_json.pop('components', None)
            if isinstance(device, Computer) and device.hid:
                device.add_mac_to_hid(components_snap=components)
        snapshot = Snapshot(**self.snapshot_json)

        # Remove new actions from devices so they don't interfere with sync
        actions_device = set(e for e in device.actions_one)
        device.actions_one.clear()
        if components:
            actions_components = tuple(
                set(e for e in c.actions_one) for c in components
            )
            for component in components:
                component.actions_one.clear()

        assert not device.actions_one
        assert all(not c.actions_one for c in components) if components else True
        db_device, remove_actions = self.resource_def.sync.run(device, components)

        del device  # Do not use device anymore
        snapshot.device = db_device
        snapshot.actions |= remove_actions | actions_device  # Set actions to snapshot
        # commit will change the order of the components by what
        # the DB wants. Let's get a copy of the list so we preserve order
        ordered_components = OrderedSet(x for x in snapshot.components)

        # Add the new actions to the db-existing devices and components
        db_device.actions_one |= actions_device
        if components:
            for component, actions in zip(ordered_components, actions_components):
                component.actions_one |= actions
                snapshot.actions |= actions

        if snapshot.software == SnapshotSoftware.Workbench:
            # Check ownership of (non-component) device to from current.user
            if db_device.owner_id != g.user.id:
                raise InsufficientPermission()
        elif snapshot.software == SnapshotSoftware.WorkbenchAndroid:
            pass  # TODO try except to compute RateMobile
        # Check if HID is null and add Severity:Warning to Snapshot
        if snapshot.device.hid is None:
            snapshot.severity = Severity.Warning

        db.session.add(snapshot)
        db.session().final_flush()
        return snapshot


api.add_url_rule('/inventory/', view_func=InventoryView.as_view('inventory'))
