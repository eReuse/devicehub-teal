from typing import Callable, Iterable, Tuple

from ereuse_devicehub.resources.device.sync import Sync
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

    def __init__(self, app, import_name=__package__, static_folder=None, static_url_path=None,
                 template_folder=None, url_prefix=None, subdomain=None, url_defaults=None,
                 root_path=None, cli_commands: Iterable[Tuple[Callable, str or None]] = tuple()):
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)
        self.sync = Sync()


class TestDef(EventDef):
    SCHEMA = Test


class TestHardDriveDef(TestDef):
    SCHEMA = TestHardDrive
