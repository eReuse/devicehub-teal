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
from ereuse_devicehub.resources.event.models import Event, RateComputer, Snapshot
from ereuse_devicehub.resources.event.rate.workbench.v1_0 import CannotRate

SUPPORTED_WORKBENCH = StrictVersion('11.0')


class EventView(View):
    def post(self):
        """Posts an event."""
        json = request.get_json(validate=False)
        if not json or 'type' not in json:
            raise ValidationError('Resource needs a type.')
        # todo there should be a way to better get subclassess resource
        #   defs
        resource_def = app.resources[json['type']]
        e = resource_def.schema.load(json)
        if json['type'] == Snapshot.t:
            return self.snapshot(e, resource_def)
        Model = db.Model._decl_class_registry.data[json['type']]()
        event = Model(**e)
        db.session.add(event)
        db.session().final_flush()
        ret = self.schema.jsonify(event)
        ret.status_code = 201
        db.session.commit()
        return ret

    def one(self, id: UUID):
        """Gets one event."""
        event = Event.query.filter_by(id=id).one()
        return self.schema.jsonify(event)

    def snapshot(self, snapshot_json: dict, resource_def):
        """
        Performs a Snapshot.

        See `Snapshot` section in docs for more info.
        """
        # Note that if we set the device / components into the snapshot
        # model object, when we flush them to the db we will flush
        # snapshot, and we want to wait to flush snapshot at the end
        device = snapshot_json.pop('device')  # type: Computer
        components = None
        if snapshot_json['software'] == SnapshotSoftware.Workbench:
            components = snapshot_json.pop('components')  # type: List[Component]
        snapshot = Snapshot(**snapshot_json)

        # Remove new events from devices so they don't interfere with sync
        events_device = set(e for e in device.events_one)
        device.events_one.clear()
        if components:
            events_components = tuple(set(e for e in c.events_one) for c in components)
            for component in components:
                component.events_one.clear()

        assert not device.events_one
        assert all(not c.events_one for c in components) if components else True
        db_device, remove_events = resource_def.sync.run(device, components)
        del device  # Do not use device anymore
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
        if snapshot.software == SnapshotSoftware.Workbench:
            try:
                rate_computer, price = RateComputer.compute(db_device)
            except CannotRate:
                pass
            else:
                snapshot.events.add(rate_computer)
                if price:
                    snapshot.events.add(price)

        db.session.add(snapshot)
        db.session().final_flush()
        ret = self.schema.jsonify(snapshot)  # transform it back
        ret.status_code = 201
        db.session.commit()
        return ret
