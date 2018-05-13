from ereuse_devicehub.resources.event.schemas import Add, Event, Remove, Snapshot, Test, \
    TestHardDrive
from ereuse_devicehub.resources.event.views import EventView, SnapshotView
from teal.resource import Converters, Resource


class EventDef(Resource):
    SCHEMA = Event
    VIEW = EventView
    AUTH = True
    ID_CONVERTER = Converters.int


class AddDef(EventDef):
    SCHEMA = Add


class RemoveDef(EventDef):
    SCHEMA = Remove


class SnapshotDef(EventDef):
    SCHEMA = Snapshot
    VIEW = SnapshotView


class TestDef(EventDef):
    SCHEMA = Test


class TestHardDriveDef(TestDef):
    SCHEMA = TestHardDrive
