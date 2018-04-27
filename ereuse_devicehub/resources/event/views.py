from distutils.version import StrictVersion

from flask import request

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.sync import Sync
from ereuse_devicehub.resources.event.enums import SoftwareType
from ereuse_devicehub.resources.event.models import Event, Snapshot, TestHardDrive
from teal.resource import View


class EventView(View):
    def one(self, id: int):
        """Gets one event."""
        return Event.query.filter_by(id=id).one()


SUPPORTED_WORKBENCH = StrictVersion('11.0')


class SnapshotView(View):
    def post(self):
        """Creates a Snapshot."""
        snapshot = Snapshot(**request.get_json())  # todo put this in schema.load()?
        # noinspection PyArgumentList
        c = snapshot.components if snapshot.software == SoftwareType.Workbench else None
        snapshot.device, snapshot.components, snapshot.events = Sync.run(snapshot.device, c)
        db.session.add(snapshot)
        # transform it back
        return self.schema.jsonify(snapshot)


class TestHardDriveView(View):
    def post(self):
        t = request.get_json()  # type: dict
        # noinspection PyArgumentList
        test = TestHardDrive(snapshot_id=t.pop('snapshot'), device_id=t.pop('device'), **t)
        return test


class StressTestView(View):
    def post(self):
        t = request.get_json()  # type: dict
