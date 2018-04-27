from ereuse_devicehub.resources.event.schemas import Snapshot, Event
from ereuse_devicehub.resources.event.views import EventView, SnapshotView
from teal.resource import Converters, Resource


class EventDef(Resource):
    SCHEMA = Event
    VIEW = EventView
    AUTH = True
    ID_CONVERTER = Converters.int


class SnapshotDef(EventDef):
    SCHEMA = Snapshot
    VIEW = SnapshotView
