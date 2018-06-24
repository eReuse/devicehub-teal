from distutils.version import StrictVersion
from typing import List
from uuid import UUID

from flask import request
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Component, Computer
from ereuse_devicehub.resources.enums import RatingSoftware, SnapshotSoftware
from ereuse_devicehub.resources.event.models import Event, ManualRate, Snapshot, WorkbenchRate
from teal.resource import View


class EventView(View):
    def one(self, id: UUID):
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
        components = s.pop('components') \
            if s['software'] == SnapshotSoftware.Workbench else None  # type: List[Component]
        snapshot = Snapshot(**s)

        # Remove new events from devices so they don't interfere with sync
        events_device = set(e for e in device.events_one)
        device.events_one.clear()
        if components:
            events_components = tuple(set(e for e in c.events_one) for c in components)
            for component in components:
                component.events_one.clear()

        # noinspection PyArgumentList
        assert not device.events_one
        assert all(not c.events_one for c in components) if components else True
        db_device, remove_events = self.resource_def.sync.run(device, components)
        snapshot.device = db_device
        snapshot.events |= remove_events | events_device
        # commit will change the order of the components by what
        # the DB wants. Let's get a copy of the list so we preserve order
        ordered_components = OrderedSet(x for x in snapshot.components)

        for event in events_device:
            if isinstance(event, ManualRate):
                event.algorithm_software = RatingSoftware.Ereuse
                event.algorithm_version = StrictVersion('1.0')
            if isinstance(event, WorkbenchRate):
                # todo process workbench rate
                event.data_storage = 2
                event.graphic_card = 4
                event.processor = 1

        # Add the new events to the db-existing devices and components
        db_device.events_one |= events_device
        if components:
            for component, events in zip(ordered_components, events_components):
                component.events_one |= events
                snapshot.events |= events

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
