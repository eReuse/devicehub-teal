""" This is the view for Snapshots """

from datetime import timedelta
from distutils.version import StrictVersion
from uuid import UUID

import ereuse_devicehub.ereuse_utils
import jwt
from flask import current_app as app
from flask import g, request

from ereuse_devicehub.db import db
from ereuse_devicehub.query import things_response
from ereuse_devicehub.resources.action.models import (
    Action,
    Allocate,
    Confirm,
    Deallocate,
    InitTransfer,
    Live,
    Revoke,
    Snapshot,
    Trade,
    VisualTest,
)
from ereuse_devicehub.resources.action.views import trade as trade_view
from ereuse_devicehub.resources.action.views.documents import ErasedView
from ereuse_devicehub.resources.action.views.snapshot import (
    SnapshotView,
    move_json,
    save_json,
)
from ereuse_devicehub.resources.device.models import Computer, DataStorage, Device
from ereuse_devicehub.resources.enums import Severity
from ereuse_devicehub.teal.db import ResourceNotFound
from ereuse_devicehub.teal.marshmallow import ValidationError
from ereuse_devicehub.teal.resource import View

SUPPORTED_WORKBENCH = StrictVersion('11.0')


class AllocateMix:
    model = None

    def post(self):
        """Create one res_obj"""
        res_json = request.get_json()
        res_obj = self.model(**res_json)
        db.session.add(res_obj)
        db.session().final_flush()
        ret = self.schema.jsonify(res_obj)
        ret.status_code = 201
        db.session.commit()
        return ret

    def find(self, args: dict):
        res_objs = (
            self.model.query.filter_by(author=g.user)
            .order_by(self.model.created.desc())
            .paginate(per_page=200)
        )
        return things_response(
            self.schema.dump(res_objs.items, many=True, nested=0),
            res_objs.page,
            res_objs.per_page,
            res_objs.total,
            res_objs.prev_num,
            res_objs.next_num,
        )


class AllocateView(AllocateMix, View):
    model = Allocate


class DeallocateView(AllocateMix, View):
    model = Deallocate


class LiveView(View):
    def post(self):
        """Posts an action."""
        res_json = request.get_json(validate=False)
        tmp_snapshots = app.config['TMP_LIVES']
        path_live = save_json(res_json, tmp_snapshots, '', live=True)
        res_json.pop('debug', None)
        res_json.pop('elapsed', None)
        res_json.pop('os', None)
        res_json_valid = self.schema.load(res_json)
        live = self.live(res_json_valid)
        db.session.add(live)
        db.session().final_flush()
        ret = self.schema.jsonify(live)
        ret.status_code = 201
        db.session.commit()
        move_json(tmp_snapshots, path_live, '', live=True)
        return ret

    def get_hdd_details(self, snapshot, device):
        """We get the liftime and serial_number of the disk"""
        usage_time_hdd = None
        serial_number = None
        components = [c for c in snapshot['components']]
        components.sort(key=lambda x: x.created)
        for hd in components:
            if not isinstance(hd, DataStorage):
                continue

            serial_number = hd.serial_number
            for act in hd.actions:
                if not act.type == "TestDataStorage":
                    continue
                usage_time_hdd = act.lifetime
                break

            if usage_time_hdd:
                break

        if not serial_number:
            """There aren't any disk"""
            raise ResourceNotFound(
                "There aren't any disk in this device {}".format(device)
            )
        return usage_time_hdd, serial_number

    def get_hid(self, snapshot):
        device = snapshot.get('device')  # type: Computer
        components = snapshot.get('components')
        if not device:
            return None
        if not components:
            return device.hid
        macs = [
            c.serial_number
            for c in components
            if c.type == 'NetworkAdapter' and c.serial_number is not None
        ]
        macs.sort()
        mac = ''
        hid = device.hid
        if not hid:
            return hid
        if macs:
            mac = "-{mac}".format(mac=macs[0])
        # hid += mac
        return hid

    def live(self, snapshot):
        """If the device.allocated == True, then this snapshot create an action live."""
        for c in snapshot['components']:
            c.parent = snapshot['device']
        snapshot['device'].set_hid()
        hid = self.get_hid(snapshot)
        if not hid or not Device.query.filter(Device.hid == hid).count():
            raise ValidationError('Device not exist.')

        device = Device.query.filter(Device.hid == hid, Device.allocated == True).one()
        # Is not necessary
        if not device:
            raise ValidationError('Device not exist.')
        if not device.allocated:
            raise ValidationError('Sorry this device is not allocated.')

        usage_time_hdd, serial_number = self.get_hdd_details(snapshot, device)

        data_live = {
            'usage_time_hdd': usage_time_hdd,
            'serial_number': serial_number,
            'snapshot_uuid': snapshot['uuid'],
            'description': '',
            'software': snapshot['software'],
            'software_version': snapshot['version'],
            'licence_version': snapshot['licence_version'],
            'author_id': device.owner_id,
            'agent_id': device.owner.individual.id,
            'device': device,
        }

        live = Live(**data_live)

        if not usage_time_hdd:
            warning = f"We don't found any TestDataStorage for disk sn: {serial_number}"
            live.severity = Severity.Warning
            live.description = warning
            return live

        live.sort_actions()
        diff_time = live.diff_time()
        if diff_time is None:
            warning = "Don't exist one previous live or snapshot as reference"
            live.description += warning
            live.severity = Severity.Warning
        elif diff_time < timedelta(0):
            warning = "The difference with the last live/snapshot is negative"
            live.description += warning
            live.severity = Severity.Warning
        return live


def decode_snapshot(data):
    try:
        return jwt.decode(
            data['data'],
            app.config['JWT_PASS'],
            algorithms="HS256",
            json_encoder=ereuse_devicehub.ereuse_utils.JSONEncoder,
        )
    except jwt.exceptions.InvalidSignatureError as err:
        txt = 'Invalid snapshot'
        raise ValidationError(txt)


class ActionView(View):
    def post(self):
        """Posts an action."""

        json = request.get_json(validate=False)

        if not json or 'type' not in json:
            raise ValidationError('Post request needs a json.')
        # todo there should be a way to better get subclassess resource
        #   defs
        resource_def = app.resources[json['type']]
        if json['type'] == Snapshot.t:
            if json.get('software') == 'Web' and json['device'] == 'Computer':
                txt = 'Invalid snapshot'
                raise ValidationError(txt)

            if json.get('software') == 'Web':
                snapshot = SnapshotView(json, resource_def, self.schema)
                return snapshot.post()

            # TODO @cayop uncomment at four weeks
            # if not 'data' in json:
            # txt = 'Invalid snapshot'
            # raise ValidationError(txt)

            # snapshot_data = decode_snapshot(json)

            snapshot_data = json
            if 'data' in json and isinstance(json['data'], str):
                snapshot_data = decode_snapshot(json)

            if not snapshot_data:
                txt = 'Invalid snapshot'
                raise ValidationError(txt)

            snapshot = SnapshotView(snapshot_data, resource_def, self.schema)
            return snapshot.post()

        if json['type'] == VisualTest.t:
            pass
            # TODO JN add compute rate with new visual test and old components device

        if json['type'] == InitTransfer.t:
            return self.transfer_ownership()

        if json['type'] == Trade.t:
            trade = trade_view.TradeView(json, resource_def, self.schema)
            return trade.post()

        if json['type'] == Confirm.t:
            confirm = trade_view.ConfirmView(json, resource_def, self.schema)
            return confirm.post()

        if json['type'] == Revoke.t:
            revoke = trade_view.RevokeView(json, resource_def, self.schema)
            return revoke.post()

        if json['type'] == 'ConfirmRevoke':
            revoke = trade_view.RevokeView(json, resource_def, self.schema)
            return revoke.post()

        if json['type'] == 'RevokeDocument':
            revoke = trade_view.RevokeDocumentView(json, resource_def, self.schema)
            return revoke.post()

        if json['type'] == 'ConfirmDocument':
            confirm = trade_view.ConfirmDocumentView(json, resource_def, self.schema)
            return confirm.post()

        if json['type'] == 'ConfirmRevokeDocument':
            confirm_revoke = trade_view.ConfirmRevokeDocumentView(
                json, resource_def, self.schema
            )
            return confirm_revoke.post()

        if json['type'] == 'DataWipe':
            erased = ErasedView(json, resource_def.schema)
            return erased.post()

        a = resource_def.schema.load(json)
        Model = db.Model._decl_class_registry.data[json['type']]()
        action = Model(**a)
        db.session.add(action)
        db.session().final_flush()
        ret = self.schema.jsonify(action)
        ret.status_code = 201
        db.session.commit()
        return ret

    def one(self, id: UUID):
        """Gets one action."""
        action = Action.query.filter_by(id=id).one()
        return self.schema.jsonify(action)

    def transfer_ownership(self):
        """Perform a InitTransfer action to change author_id of device"""
        pass
