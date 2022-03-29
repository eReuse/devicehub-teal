""" This is the view for Snapshots """

import json
import os
import shutil
from datetime import datetime

from flask import current_app as app
from flask import g
from flask.json import jsonify
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.db import db
from ereuse_devicehub.parser.parser import ParseSnapshot, ParseSnapshotLsHw
from ereuse_devicehub.resources.action.models import RateComputer, Snapshot
from ereuse_devicehub.resources.action.rate.v1_0 import CannotRate
from ereuse_devicehub.resources.action.schemas import Snapshot_lite
from ereuse_devicehub.resources.device.models import Computer
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


class SnapshotView:
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
        if snapshot_json.get('version') in ["2022.03"]:
            self.validate_json(snapshot_json)
            self.response = self.build_lite()
        else:
            self.snapshot_json = resource_def.schema.load(snapshot_json)
            self.response = self.build()
        move_json(self.tmp_snapshots, self.path_snapshot, g.user.email)

    def post(self):
        return self.response

    def build(self):
        device = self.snapshot_json.pop('device')  # type: Computer
        components = None
        if self.snapshot_json['software'] == (
            SnapshotSoftware.Workbench or SnapshotSoftware.WorkbenchAndroid
        ):
            components = self.snapshot_json.pop(
                'components', None
            )  # type: List[Component]
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
            # Compute ratings
            # try:
            #     rate_computer, price = RateComputer.compute(db_device)
            # except CannotRate:
            #     pass
            # else:
            #     snapshot.actions.add(rate_computer)
            #     if price:
            #         snapshot.actions.add(price)
        elif snapshot.software == SnapshotSoftware.WorkbenchAndroid:
            pass  # TODO try except to compute RateMobile
        # Check if HID is null and add Severity:Warning to Snapshot
        if snapshot.device.hid is None:
            snapshot.severity = Severity.Warning

        db.session.add(snapshot)
        db.session().final_flush()
        ret = self.schema.jsonify(snapshot)  # transform it back
        ret.status_code = 201
        db.session.commit()
        return ret

    def validate_json(self, snapshot_json):
        self.schema2 = Snapshot_lite()
        self.snapshot_json = self.schema2.load(snapshot_json)

    def build_lite(self):
        snap = ParseSnapshotLsHw(self.snapshot_json)
        # snap = ParseSnapshot(self.snapshot_json)
        self.snapshot_json = self.resource_def.schema.load(snap.snapshot_json)
        return self.build()
