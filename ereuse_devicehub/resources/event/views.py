from distutils.version import StrictVersion

from flask import request
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Computer
from ereuse_devicehub.resources.enums import SnapshotSoftware
from ereuse_devicehub.resources.event.models import Event, Snapshot, TestDataStorage
from teal.resource import View


class EventView(View):
    def one(self, id: int):
        """Gets one event."""
        event = Event.query.filter_by(id=id).one()
        return self.schema.jsonify(event)


SUPPORTED_WORKBENCH = StrictVersion('11.0')


class SnapshotView(View):
    def post(self):
        """
        Performs a Snapshot.

        See `Snapshot` section in docs for more info.
        """
        s = request.get_json()
        # Note that if we set the device / components into the snapshot
        # model object, when we flush them to the db we will flush
        # snapshot, and we want to wait to flush snapshot at the end
        device = s.pop('device')  # type: Computer
        components = s.pop('components') if s['software'] == SnapshotSoftware.Workbench else None
        if 'events' in s:
            events = s.pop('events')
            # todo perform events
        # noinspection PyArgumentList
        snapshot = Snapshot(**s)
        snapshot.device, snapshot.events = self.resource_def.sync.run(device, components)
        snapshot.components = snapshot.device.components
        # todo compute rating
        # commit will change the order of the components by what
        # the DB wants. Let's get a copy of the list so we preserve order
        ordered_components = OrderedSet(x for x in snapshot.components)
        db.session.add(snapshot)
        db.session.commit()
        # todo we are setting snapshot dirty again with this components but
        # we do not want to update it.
        # The real solution is https://stackoverflow.com/questions/
        # 24480581/set-the-insert-order-of-a-many-to-many-sqlalchemy-
        # flask-app-sqlite-db?noredirect=1&lq=1
        snapshot.components = ordered_components
        ret = self.schema.jsonify(snapshot)  # transform it back
        ret.status_code = 201
        return ret


class TestHardDriveView(View):
    def post(self):
        t = request.get_json()  # type: dict
        # noinspection PyArgumentList
        test = TestDataStorage(snapshot_id=t.pop('snapshot'), device_id=t.pop('device'), **t)
        return test


class StressTestView(View):
    def post(self):
        t = request.get_json()  # type: dict
