""" This is the view for Snapshots """

import copy
import json
import os
import shutil
from datetime import datetime
from uuid import UUID

from flask import current_app as app
from flask import g
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import EraseBasic, Snapshot
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


class SnapshotMixin:
    sync = Sync()

    def build(self, snapshot_json=None, create_new_device=False):  # noqa: C901
        self.create_new_device = create_new_device
        if not snapshot_json:
            snapshot_json = self.snapshot_json
        device = snapshot_json.pop('device')  # type: Computer
        components = None
        if snapshot_json['software'] == (
            SnapshotSoftware.Workbench or SnapshotSoftware.WorkbenchAndroid
        ):
            components = snapshot_json.pop('components', None)
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
        db_device, remove_actions = self.sync.run(
            device, components, self.create_new_device
        )

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

        self.is_server_erase(snapshot)

        snapshot.device.set_hid()
        snapshot.device.binding.device.set_hid()

        snapshot.create_json_hw(self.json_wb)
        snapshot.device.register_dlt()
        snapshot.register_passport_dlt()

        for ac in snapshot.actions:
            if not isinstance(ac, EraseBasic):
                continue
            ac.register_proof()

        return snapshot

    def is_server_erase(self, snapshot):
        if snapshot.device.binding:
            if snapshot.device.binding.kangaroo:
                snapshot.is_server_erase = True

    def get_old_smbios_version(self, debug):
        capabilities = debug.get('lshw', {}).get('capabilities', {})
        for x in capabilities.values():
            if "SMBIOS version" in x:
                e = x.split("SMBIOS version ")[1].split(".")
                if int(e[0]) < 3 and int(e[1]) < 6:
                    self.errors(txt=x)
                    return True
        return False

    def get_uuid(self, debug):
        if not debug or not isinstance(debug, dict):
            self.errors(txt="There is not uuid")
            return

        if self.get_old_smbios_version(debug):
            return

        hw_uuid = debug.get('lshw', {}).get('configuration', {}).get('uuid')

        if not hw_uuid:
            self.errors(txt="There is not uuid")
            return

        uuid = UUID(hw_uuid)
        return UUID(bytes_le=uuid.bytes)

    def get_fields_extra(self, debug, snapshot_json):
        if not debug or not isinstance(debug, dict):
            return

        lshw = debug.get('lshw', {})

        family = lshw.get('configuration', {}).get('family', '')

        snapshot_json['device']['family'] = family

        # lshw_mothers = []
        # for mt in lshw.get('children', []):
        #     if mt.get('description') == "Motherboard":
        #         lshw_mothers.append(mt)

        # for comp in snapshot_json.get('components', []):
        #     if comp.get('type') != 'Motherboard':
        #         continue
        #     for mt in lshw_mothers:
        #         if comp['serialNumber'] == mt.get('serial', ''):
        #             comp['vendor'] = mt.get('vendor', '')
        #             comp['product'] = mt.get('product', '')
        #             comp['version'] = mt.get('version', '')

    def errors(self, txt=None, severity=Severity.Error, snapshot=None, commit=False):
        if not txt:
            return

        from ereuse_devicehub.parser.models import SnapshotsLog

        error = SnapshotsLog(
            description=txt,
            snapshot_uuid=self.uuid,
            severity=severity,
            sid=self.sid,
            version=self.version,
            snapshot=snapshot,
        )
        error.save(commit=commit)


class SnapshotView(SnapshotMixin):
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
        self.json_wb = copy.copy(snapshot_json)
        self.path_snapshot = save_json(snapshot_json, self.tmp_snapshots, g.user.email)
        self.version = snapshot_json.get('version')
        self.uuid = snapshot_json.get('uuid')
        self.sid = None
        self.debug = snapshot_json.pop('debug', {})
        system_uuid = self.get_uuid(self.debug)
        if system_uuid:
            snapshot_json['device']['system_uuid'] = system_uuid

        self.get_fields_extra(self.debug, snapshot_json)

        try:
            self.snapshot_json = resource_def.schema.load(snapshot_json)
            snapshot = self.build()
        except Exception as err:
            txt = "{}".format(err)
            self.errors(txt=txt, commit=True)
            raise err

        db.session.add(snapshot)
        self.errors(txt="Ok", severity=Severity.Info, snapshot=snapshot, commit=False)

        db.session().final_flush()
        self.response = self.schema.jsonify(snapshot)  # transform it back
        self.response.status_code = 201
        db.session.commit()
        move_json(self.tmp_snapshots, self.path_snapshot, g.user.email)

    def post(self):
        return self.response
