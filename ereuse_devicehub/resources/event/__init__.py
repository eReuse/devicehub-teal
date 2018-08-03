from typing import Callable, Iterable, Tuple

from ereuse_devicehub.resources.device.sync import Sync
from ereuse_devicehub.resources.event import schemas
from ereuse_devicehub.resources.event.views import EventView, SnapshotView
from teal.resource import Converters, Resource


class EventDef(Resource):
    SCHEMA = schemas.Event
    VIEW = EventView
    AUTH = True
    ID_CONVERTER = Converters.uuid


class AddDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Add


class RemoveDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Remove


class EraseBasicDef(EventDef):
    VIEW = None
    SCHEMA = schemas.EraseBasic


class EraseSectorsDef(EraseBasicDef):
    VIEW = None
    SCHEMA = schemas.EraseSectors


class StepDef(Resource):
    VIEW = None
    SCHEMA = schemas.Step


class StepZeroDef(StepDef):
    VIEW = None
    SCHEMA = schemas.StepZero


class StepRandomDef(StepDef):
    VIEW = None
    SCHEMA = schemas.StepRandom


class RateDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Rate


class AggregateRateDef(RateDef):
    VIEW = None
    SCHEMA = schemas.AggregateRate


class WorkbenchRateDef(RateDef):
    VIEW = None
    SCHEMA = schemas.WorkbenchRate


class PhotoboxUserDef(RateDef):
    VIEW = None
    SCHEMA = schemas.PhotoboxUserRate


class PhotoboxSystemRateDef(RateDef):
    VIEW = None
    SCHEMA = schemas.PhotoboxSystemRate


class AppRateDef(RateDef):
    VIEW = None
    SCHEMA = schemas.AppRate


class PriceDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Price


class EreusePriceDef(EventDef):
    VIEW = None
    SCHEMA = schemas.EreusePrice


class InstallDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Install


class SnapshotDef(EventDef):
    VIEW = SnapshotView
    SCHEMA = schemas.Snapshot

    def __init__(self, app, import_name=__package__, static_folder=None, static_url_path=None,
                 template_folder=None, url_prefix=None, subdomain=None, url_defaults=None,
                 root_path=None, cli_commands: Iterable[Tuple[Callable, str or None]] = tuple()):
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)
        self.sync = Sync()


class TestDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Test


class TestDataStorageDef(TestDef):
    VIEW = None
    SCHEMA = schemas.TestDataStorage


class StressTestDef(TestDef):
    VIEW = None
    SCHEMA = schemas.StressTest


class BenchmarkDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Benchmark


class BenchmarkDataStorageDef(BenchmarkDef):
    VIEW = None
    SCHEMA = schemas.BenchmarkDataStorage


class BenchmarkWithRateDef(BenchmarkDef):
    VIEW = None
    SCHEMA = schemas.BenchmarkWithRate


class BenchmarkProcessorDef(BenchmarkWithRateDef):
    VIEW = None
    SCHEMA = schemas.BenchmarkProcessor


class BenchmarkProcessorSysbenchDef(BenchmarkProcessorDef):
    VIEW = None
    SCHEMA = schemas.BenchmarkProcessorSysbench


class BenchmarkRamSysbenchDef(BenchmarkWithRateDef):
    VIEW = None
    SCHEMA = schemas.BenchmarkRamSysbench


class ToRepairDef(EventDef):
    VIEW = None
    SCHEMA = schemas.ToRepair


class RepairDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Repair


class ReadyToUse(EventDef):
    VIEW = None
    SCHEMA = schemas.ReadyToUse


class ToPrepareDef(EventDef):
    VIEW = None
    SCHEMA = schemas.ToPrepare


class PrepareDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Prepare


class LiveDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Live


class ReserveDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Reserve


class CancelReservationDef(EventDef):
    VIEW = None
    SCHEMA = schemas.CancelReservation


class SellDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Sell


class DonateDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Donate


class RentDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Rent


class CancelTradeDef(EventDef):
    VIEW = None
    SCHEMA = schemas.CancelTrade


class ToDisposeProductDef(EventDef):
    VIEW = None
    SCHEMA = schemas.ToDisposeProduct


class DisposeProductDef(EventDef):
    VIEW = None
    SCHEMA = schemas.DisposeProduct


class ReceiveDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Receive


class MigrateToDef(EventDef):
    VIEW = None
    SCHEMA = schemas.MigrateTo


class MigrateFromDef(EventDef):
    VIEW = None
    SCHEMA = schemas.MigrateFrom
