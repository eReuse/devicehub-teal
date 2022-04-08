""" This is the view for Snapshots """

import json
import os
import shutil
from datetime import datetime

from flask import current_app as app
from flask import g
from marshmallow import ValidationError
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.db import db
from ereuse_devicehub.parser.models import SnapshotErrors
from ereuse_devicehub.parser.parser import ParseSnapshotLsHw
from ereuse_devicehub.parser.schemas import Snapshot_lite
from ereuse_devicehub.resources.action.models import Snapshot
from ereuse_devicehub.resources.device.models import Computer
from ereuse_devicehub.resources.device.sync import Sync
from ereuse_devicehub.resources.enums import Severity, SnapshotSoftware
from ereuse_devicehub.resources.user.exceptions import InsufficientPermission


def save_json(req_json, tmp_snapshots, user, live=False):
    """
    This function allow save a snapshot in json format un a TMP_SNAPSHOTS directory
    The file need to be saved with one name format with the stamptime and uuid joins
    """
    uuid = req_json.get('uuid', '')
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour
    minutes = now.minute

    name_file = f"{year}-{month}-{day}-{hour}-{minutes}_{user}_{uuid}.json"
    path_dir_base = os.path.join(tmp_snapshots, user)
    if live:
        path_dir_base = tmp_snapshots
    path_errors = os.path.join(path_dir_base, 'errors')
    path_fixeds = os.path.join(path_dir_base, 'fixeds')
    path_name = os.path.join(path_errors, name_file)

    if not os.path.isdir(path_dir_base):
        os.system(f'mkdir -p {path_errors}')
        os.system(f'mkdir -p {path_fixeds}')

    with open(path_name, 'w') as snapshot_file:
        snapshot_file.write(json.dumps(req_json))

    return path_name


def move_json(tmp_snapshots, path_name, user, live=False):
    """
    This function move the json than it's correct
    """
    path_dir_base = os.path.join(tmp_snapshots, user)
    if live:
        path_dir_base = tmp_snapshots
    if os.path.isfile(path_name):
        shutil.copy(path_name, path_dir_base)
        os.remove(path_name)


class SnapshotMix:
    sync = Sync()

    def build(self, snapshot_json=None):  # noqa: C901
        if not snapshot_json:
            snapshot_json = self.snapshot_json
        device = snapshot_json.pop('device')  # type: Computer
        components = None
        if snapshot_json['software'] == (
            SnapshotSoftware.Workbench or SnapshotSoftware.WorkbenchAndroid
        ):
            components = snapshot_json.pop('components', None)  # type: List[Component]
            if isinstance(device, Computer) and device.hid:
                device.add_mac_to_hid(components_snap=components)
        snapshot = Snapshot(**snapshot_json)

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
        db_device, remove_actions = self.sync.run(device, components)

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

        return snapshot


class SnapshotView(SnapshotMix):
    """Performs a Snapshot.

    See `Snapshot` section in docs for more info.
    """

    # Note that if we set the device / components into the snapshot
    # model object, when we flush them to the db we will flush
    # snapshot, and we want to wait to flush snapshot at the end

    def __init__(self, snapshot_json: dict, resource_def, schema):
        self.schema = schema
        self.resource_def = resource_def
        self.tmp_snapshots = app.config['TMP_SNAPSHOTS']
        self.path_snapshot = save_json(snapshot_json, self.tmp_snapshots, g.user.email)
        snapshot_json.pop('debug', None)
        try:
            self.snapshot_json = resource_def.schema.load(snapshot_json)
        except ValidationError as err:
            txt = "{}".format(err)
            uuid = snapshot_json.get('uuid')
            error = SnapshotErrors(
                description=txt, snapshot_uuid=uuid, severity=Severity.Error
            )
            error.save(commit=True)
            raise err

        snapshot = self.build()
        db.session.add(snapshot)
        db.session().final_flush()
        self.response = self.schema.jsonify(snapshot)  # transform it back
        self.response.status_code = 201
        db.session.commit()
        move_json(self.tmp_snapshots, self.path_snapshot, g.user.email)

    def post(self):
        return self.response
