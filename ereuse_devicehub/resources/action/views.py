""" This is the view for Snapshots """

import os
import json
from datetime import datetime
from distutils.version import StrictVersion
from uuid import UUID

from flask import current_app as app, request, g
from sqlalchemy.util import OrderedSet
from teal.marshmallow import ValidationError
from teal.resource import View

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import Action, RateComputer, Snapshot, VisualTest, \
    InitTransfer
from ereuse_devicehub.resources.action.rate.v1_0 import CannotRate
from ereuse_devicehub.resources.enums import SnapshotSoftware, Severity
from ereuse_devicehub.resources.user.exceptions import InsufficientPermission

SUPPORTED_WORKBENCH = StrictVersion('11.0')


def save_json(req_json, tmp_snapshots, user):
    """
    This function allow save a snapshot in json format un a TMP_SNAPSHOTS directory
    The file need to be saved with one name format with the stamptime and uuid joins
    """
    uuid = req_json.get('uuid', '')
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day

    name_file = f"{uuid}_{user}_{year}-{month}-{day}.json"
    path_name = os.path.join(tmp_snapshots, name_file)

    if not os.path.isdir(tmp_snapshots):
        os.system('mkdir -p {}'.format(tmp_snapshots))

    with open(path_name, 'w') as snapshot_file:
        snapshot_file.write(json.dumps(req_json))

    return path_name


class ActionView(View):
    def post(self):
        """Posts an action."""
        json = request.get_json(validate=False)
        tmp_snapshots = app.config['TMP_SNAPSHOTS']
        path_snapshot = save_json(json, tmp_snapshots, g.user.email)
        if not json or 'type' not in json:
            raise ValidationError('Resource needs a type.')
        # todo there should be a way to better get subclassess resource
        #   defs
        resource_def = app.resources[json['type']]
        a = resource_def.schema.load(json)
        if json['type'] == Snapshot.t:
            response = self.snapshot(a, resource_def)
            os.remove(path_snapshot)
            return response
        if json['type'] == VisualTest.t:
            pass
            # TODO JN add compute rate with new visual test and old components device
        if json['type'] == InitTransfer.t:
            os.remove(path_snapshot)
            return self.transfer_ownership()
        Model = db.Model._decl_class_registry.data[json['type']]()
        action = Model(**a)
        db.session.add(action)
        db.session().final_flush()
        ret = self.schema.jsonify(action)
        ret.status_code = 201
        db.session.commit()
        os.remove(path_snapshot)
        return ret

    def one(self, id: UUID):
        """Gets one action."""
        action = Action.query.filter_by(id=id).one()
        return self.schema.jsonify(action)

    def snapshot(self, snapshot_json: dict, resource_def):
        """Performs a Snapshot.

        See `Snapshot` section in docs for more info.
        """
        # Note that if we set the device / components into the snapshot
        # model object, when we flush them to the db we will flush
        # snapshot, and we want to wait to flush snapshot at the end

        device = snapshot_json.pop('device')  # type: Computer
        components = None
        if snapshot_json['software'] == (SnapshotSoftware.Workbench or SnapshotSoftware.WorkbenchAndroid):
            components = snapshot_json.pop('components', None)  # type: List[Component]
        snapshot = Snapshot(**snapshot_json)

        # Remove new actions from devices so they don't interfere with sync
        actions_device = set(e for e in device.actions_one)
        device.actions_one.clear()
        if components:
            actions_components = tuple(set(e for e in c.actions_one) for c in components)
            for component in components:
                component.actions_one.clear()

        assert not device.actions_one
        assert all(not c.actions_one for c in components) if components else True
        db_device, remove_actions = resource_def.sync.run(device, components)

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
            try:
                rate_computer, price = RateComputer.compute(db_device)
            except CannotRate:
                pass
            else:
                snapshot.actions.add(rate_computer)
                if price:
                    snapshot.actions.add(price)
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

    def transfer_ownership(self):
        """Perform a InitTransfer action to change author_id of device"""
        pass
