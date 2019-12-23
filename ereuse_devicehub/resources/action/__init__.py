from typing import Callable, Iterable, Tuple

from teal.resource import Converters, Resource

from ereuse_devicehub.resources.action import schemas
from ereuse_devicehub.resources.action.views import ActionView
from ereuse_devicehub.resources.device.sync import Sync


class ActionDef(Resource):
    SCHEMA = schemas.Action
    VIEW = ActionView
    AUTH = True
    ID_CONVERTER = Converters.uuid


class AddDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Add


class RemoveDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Remove


class EraseBasicDef(ActionDef):
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


class BenchmarkDef(ActionDef):
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


class TestDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Test


class MeasureBattery(TestDef):
    VIEW = None
    SCHEMA = schemas.MeasureBattery


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


class VisualTestDef(TestDef):
    VIEW = None
    SCHEMA = schemas.VisualTest


class RateDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Rate


class RateComputerDef(RateDef):
    VIEW = None
    SCHEMA = schemas.RateComputer


class PriceDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Price


class EreusePriceDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.EreusePrice


class InstallDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Install


class SnapshotDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Snapshot

    def __init__(self, app, import_name=__name__.split('.')[0], static_folder=None,
                 static_url_path=None,
                 template_folder=None, url_prefix=None, subdomain=None, url_defaults=None,
                 root_path=None, cli_commands: Iterable[Tuple[Callable, str or None]] = tuple()):
        url_prefix = '/{}'.format(ActionDef.resource)
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)
        self.sync = Sync()


class ToRepairDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.ToRepair


class RepairDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Repair


class ReadyDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Ready


class ToPrepareDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.ToPrepare


class PrepareDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Prepare


class LiveDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Live


class ReserveDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Reserve


class CancelReservationDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.CancelReservation


class SellDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Sell


class DonateDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Donate


class RentDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Rent


class MakeAvailable(ActionDef):
    VIEW = None
    SCHEMA = schemas.MakeAvailable


class CancelTradeDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.CancelTrade


class ToDisposeProductDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.ToDisposeProduct


class DisposeProductDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.DisposeProduct


class ReceiveDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Receive


class MigrateToDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.MigrateTo


class MigrateFromDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.MigrateFrom

class TransferredDef(ActionDef):
    VIEW = None
    SCHEMA = schemas.Transferred