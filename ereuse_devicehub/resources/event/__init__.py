from typing import Callable, Iterable, Tuple

from ereuse_devicehub.resources.device.sync import Sync
from ereuse_devicehub.resources.event.schemas import Add, AggregateRate, AppRate, Benchmark, \
    BenchmarkDataStorage, BenchmarkProcessor, BenchmarkProcessorSysbench, BenchmarkRamSysbench, \
    BenchmarkWithRate, EraseBasic, EraseSectors, Event, Install, PhotoboxSystemRate, \
    PhotoboxUserRate, Rate, Remove, Snapshot, Step, StepRandom, StepZero, StressTest, Test, \
    TestDataStorage, WorkbenchRate
from ereuse_devicehub.resources.event.views import EventView, SnapshotView
from teal.resource import Converters, Resource


class EventDef(Resource):
    SCHEMA = Event
    VIEW = EventView
    AUTH = True
    ID_CONVERTER = Converters.uuid


class AddDef(EventDef):
    VIEW = None
    SCHEMA = Add


class RemoveDef(EventDef):
    VIEW = None
    SCHEMA = Remove


class EraseBasicDef(EventDef):
    VIEW = None
    SCHEMA = EraseBasic


class EraseSectorsDef(EraseBasicDef):
    VIEW = None
    SCHEMA = EraseSectors


class StepDef(Resource):
    VIEW = None
    SCHEMA = Step


class StepZeroDef(StepDef):
    VIEW = None
    SCHEMA = StepZero


class StepRandomDef(StepDef):
    VIEW = None
    SCHEMA = StepRandom


class RateDef(EventDef):
    VIEW = None
    SCHEMA = Rate


class AggregateRateDef(RateDef):
    VIEW = None
    SCHEMA = AggregateRate


class WorkbenchRateDef(RateDef):
    VIEW = None
    SCHEMA = WorkbenchRate


class PhotoboxUserDef(RateDef):
    VIEW = None
    SCHEMA = PhotoboxUserRate


class PhotoboxSystemRateDef(RateDef):
    VIEW = None
    SCHEMA = PhotoboxSystemRate


class AppRateDef(RateDef):
    VIEW = None
    SCHEMA = AppRate


class InstallDef(EventDef):
    VIEW = None
    SCHEMA = Install


class SnapshotDef(EventDef):
    VIEW = None
    SCHEMA = Snapshot
    VIEW = SnapshotView

    def __init__(self, app, import_name=__package__, static_folder=None, static_url_path=None,
                 template_folder=None, url_prefix=None, subdomain=None, url_defaults=None,
                 root_path=None, cli_commands: Iterable[Tuple[Callable, str or None]] = tuple()):
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)
        self.sync = Sync()


class TestDef(EventDef):
    VIEW = None
    SCHEMA = Test


class TestDataStorageDef(TestDef):
    VIEW = None
    SCHEMA = TestDataStorage


class StressTestDef(TestDef):
    VIEW = None
    SCHEMA = StressTest


class BenchmarkDef(EventDef):
    VIEW = None
    SCHEMA = Benchmark


class BenchmarkDataStorageDef(BenchmarkDef):
    VIEW = None
    SCHEMA = BenchmarkDataStorage


class BenchmarkWithRateDef(BenchmarkDef):
    VIEW = None
    SCHEMA = BenchmarkWithRate


class BenchmarkProcessorDef(BenchmarkWithRateDef):
    VIEW = None
    SCHEMA = BenchmarkProcessor


class BenchmarkProcessorSysbenchDef(BenchmarkProcessorDef):
    VIEW = None
    SCHEMA = BenchmarkProcessorSysbench


class BenchmarkRamSysbenchDef(BenchmarkWithRateDef):
    VIEW = None
    SCHEMA = BenchmarkRamSysbench
