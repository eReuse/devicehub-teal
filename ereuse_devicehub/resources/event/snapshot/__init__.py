from ereuse_devicehub.resources.event import EventDef
from ereuse_devicehub.resources.event.snapshot.views import SnapshotView


class SnapshotDef(EventDef):
    VIEW = SnapshotView
    SCHEMA = None
