from distutils.version import StrictVersion
from typing import List
from uuid import UUID

from flask import current_app as app, request
from sqlalchemy.util import OrderedSet
from teal.marshmallow import ValidationError
from teal.resource import View

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Component, Computer
from ereuse_devicehub.resources.enums import SnapshotSoftware
from ereuse_devicehub.resources.event.models import Event, Snapshot, WorkbenchRate


class EventView(View):
    def post(self):
        """Posts an event."""
        json = request.get_json(validate=False)
        if 'type' not in json:
            raise ValidationError('Resource needs a type.')
        e = app.resources[json['type']].schema.load(json)
        Model = db.Model._decl_class_registry.data[json['type']]()
        event = Model(**e)
        db.session.add(event)
        db.session.commit()
        ret = self.schema.jsonify(event)
        ret.status_code = 201
        return ret

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
        snapshot.events |= remove_events | events_device  # Set events to snapshot
        # commit will change the order of the components by what
        # the DB wants. Let's get a copy of the list so we preserve order
        ordered_components = OrderedSet(x for x in snapshot.components)

        # Add the new events to the db-existing devices and components
        db_device.events_one |= events_device
        if components:
            for component, events in zip(ordered_components, events_components):
                component.events_one |= events
                snapshot.events |= events

        # Compute ratings
        for rate in (e for e in events_device if isinstance(e, WorkbenchRate)):
            rates = rate.ratings()
            snapshot.events |= rates

        db.session.add(snapshot)
        db.session.commit()
        ret = self.schema.jsonify(snapshot)  # transform it back
        ret.status_code = 201
        return ret
