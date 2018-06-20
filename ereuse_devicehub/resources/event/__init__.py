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
    SCHEMA = Add


class RemoveDef(EventDef):
    SCHEMA = Remove


class EraseBasicDef(EventDef):
    SCHEMA = EraseBasic


class EraseSectorsDef(EraseBasicDef):
    SCHEMA = EraseSectors


class StepDef(Resource):
    SCHEMA = Step


class StepZeroDef(StepDef):
    SCHEMA = StepZero


class StepRandomDef(StepDef):
    SCHEMA = StepRandom


class RateDef(EventDef):
    SCHEMA = Rate


class AggregateRateDef(RateDef):
    SCHEMA = AggregateRate


class WorkbenchRateDef(RateDef):
    SCHEMA = WorkbenchRate


class PhotoboxUserDef(RateDef):
    SCHEMA = PhotoboxUserRate


class PhotoboxSystemRateDef(RateDef):
    SCHEMA = PhotoboxSystemRate


class AppRateDef(RateDef):
    SCHEMA = AppRate


class InstallDef(EventDef):
    SCHEMA = Install


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


class TestDataStorageDef(TestDef):
    SCHEMA = TestDataStorage


class StressTestDef(TestDef):
    SCHEMA = StressTest


class BenchmarkDef(EventDef):
    SCHEMA = Benchmark


class BenchmarkDataStorageDef(BenchmarkDef):
    SCHEMA = BenchmarkDataStorage


class BenchmarkWithRateDef(BenchmarkDef):
    SCHEMA = BenchmarkWithRate


class BenchmarkProcessorDef(BenchmarkWithRateDef):
    SCHEMA = BenchmarkProcessor


class BenchmarkProcessorSysbenchDef(BenchmarkProcessorDef):
    SCHEMA = BenchmarkProcessorSysbench


class BenchmarkRamSysbenchDef(BenchmarkWithRateDef):
    SCHEMA = BenchmarkRamSysbench
