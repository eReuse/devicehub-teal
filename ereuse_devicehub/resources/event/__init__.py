from typing import Callable, Iterable, Tuple

from teal.resource import Converters, Resource

from ereuse_devicehub.resources.device.sync import Sync
from ereuse_devicehub.resources.event import schemas
from ereuse_devicehub.resources.event.views import EventView


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


class ErasePhysicalDef(EraseBasicDef):
    VIEW = None
    SCHEMA = schemas.ErasePhysical


class StepDef(Resource):
    VIEW = None
    SCHEMA = schemas.Step


class StepZeroDef(StepDef):
    VIEW = None
    SCHEMA = schemas.StepZero


class StepRandomDef(StepDef):
    VIEW = None
    SCHEMA = schemas.StepRandom


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


class TestDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Test


class TestDataStorageDef(TestDef):
    VIEW = None
    SCHEMA = schemas.TestDataStorage


class StressTestDef(TestDef):
    VIEW = None
    SCHEMA = schemas.StressTest


class TestAudioDef(TestDef):
    VIEW = None
    SCHEMA = schemas.TestAudio


class TestConnectivityDef(TestDef):
    VIEW = None
    SCHEMA = schemas.TestConnectivity


class TestBatteryDef(TestDef):
    VIEW = None
    SCHEMA = schemas.TestBattery


class TestCameraDef(TestDef):
    VIEW = None
    SCHEMA = schemas.TestCamera


class TestKeyboardDef(TestDef):
    VIEW = None
    SCHEMA = schemas.TestKeyboard


class TestTrackpadDef(TestDef):
    VIEW = None
    SCHEMA = schemas.TestTrackpad


class TestBiosDef(TestDef):
    VIEW = None
    SCHEMA = schemas.TestBios


class TestVisualDef(TestDef):
    VIEW = None
    SCHEMA = schemas.TestVisual


class RateDef(EventDef):
    VIEW = None
    SCHEMA = schemas.Rate


class RateComputerDef(RateDef):
    VIEW = None
    SCHEMA = schemas.RateComputer


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
    VIEW = None
    SCHEMA = schemas.Snapshot

    def __init__(self, app, import_name=__name__.split('.')[0], static_folder=None,
                 static_url_path=None,
                 template_folder=None, url_prefix=None, subdomain=None, url_defaults=None,
                 root_path=None, cli_commands: Iterable[Tuple[Callable, str or None]] = tuple()):
        url_prefix = '/{}'.format(EventDef.resource)
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)
        self.sync = Sync()


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
