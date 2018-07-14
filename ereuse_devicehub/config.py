from distutils.version import StrictVersion
from typing import Set

from ereuse_devicehub.resources.device import CellphoneDef, ComponentDef, ComputerDef, \
    ComputerMonitorDef, DataStorageDef, DesktopDef, DeviceDef, DisplayDef, GraphicCardDef, \
    HardDriveDef, LaptopDef, MobileDef, MonitorDef, MotherboardDef, NetworkAdapterDef, \
    ProcessorDef, RamModuleDef, ServerDef, SmartphoneDef, SolidStateDriveDef, SoundCardDef, \
    TabletDef, TelevisionSetDef
from ereuse_devicehub.resources.enums import PriceSoftware, RatingSoftware
from ereuse_devicehub.resources.event import AddDef, AggregateRateDef, AppRateDef, \
    BenchmarkDataStorageDef, BenchmarkDef, BenchmarkProcessorDef, BenchmarkProcessorSysbenchDef, \
    BenchmarkRamSysbenchDef, BenchmarkWithRateDef, EraseBasicDef, EraseSectorsDef, EreusePriceDef, \
    EventDef, InstallDef, PhotoboxSystemRateDef, PhotoboxUserDef, PriceDef, RateDef, RemoveDef, \
    SnapshotDef, StepDef, StepRandomDef, StepZeroDef, StressTestDef, TestDataStorageDef, TestDef, \
    WorkbenchRateDef
from ereuse_devicehub.resources.inventory import InventoryDef
from ereuse_devicehub.resources.tag import TagDef
from ereuse_devicehub.resources.user import OrganizationDef, UserDef
from teal.auth import TokenAuth
from teal.config import Config
from teal.currency import Currency


class DevicehubConfig(Config):
    RESOURCE_DEFINITIONS = {
        DeviceDef, ComputerDef, DesktopDef, LaptopDef, ServerDef, MonitorDef, TelevisionSetDef,
        ComputerMonitorDef, ComponentDef, GraphicCardDef, DataStorageDef,
        SolidStateDriveDef, MobileDef, DisplayDef, SmartphoneDef, TabletDef, CellphoneDef,
        HardDriveDef, MotherboardDef, NetworkAdapterDef, RamModuleDef, ProcessorDef, SoundCardDef,
        UserDef,
        OrganizationDef, TagDef, EventDef, AddDef, RemoveDef, EraseBasicDef, EraseSectorsDef,
        StepDef, StepZeroDef, StepRandomDef, RateDef, AggregateRateDef, WorkbenchRateDef,
        PhotoboxUserDef, PhotoboxSystemRateDef, PriceDef, EreusePriceDef,
        InstallDef, SnapshotDef, TestDef,
        TestDataStorageDef, StressTestDef, WorkbenchRateDef, InventoryDef, BenchmarkDef,
        BenchmarkDataStorageDef, BenchmarkWithRateDef, AppRateDef, BenchmarkProcessorDef,
        BenchmarkProcessorSysbenchDef, BenchmarkRamSysbenchDef
    }
    PASSWORD_SCHEMES = {'pbkdf2_sha256'}  # type: Set[str]
    SQLALCHEMY_DATABASE_URI = 'postgresql://dhub:ereuse@localhost/devicehub'  # type: str
    SCHEMA = 'dhub'
    MIN_WORKBENCH = StrictVersion('11.0a1')  # type: StrictVersion
    """
    the minimum version of ereuse.org workbench that this devicehub
    accepts. we recommend not changing this value.
    """
    ORGANIZATION_NAME = None  # type: str
    ORGANIZATION_TAX_ID = None  # type: str
    """
    The organization using this Devicehub.
    
    It is used by default, for example, when creating tags.
    """
    API_DOC_CONFIG_TITLE = 'Devicehub'
    API_DOC_CONFIG_VERSION = '0.2'
    API_DOC_CONFIG_COMPONENTS = {
        'securitySchemes': {
            'bearerAuth': TokenAuth.API_DOCS
        }
    }
    API_DOC_CLASS_DISCRIMINATOR = 'type'

    WORKBENCH_RATE_SOFTWARE = RatingSoftware.ECost
    WORKBENCH_RATE_VERSION = StrictVersion('1.0')
    PHOTOBOX_RATE_SOFTWARE = RatingSoftware.ECost
    PHOTOBOX_RATE_VERSION = StrictVersion('1.0')
    """
    Official versions for WorkbenchRate and PhotoboxRate
    """
    PRICE_SOFTWARE = PriceSoftware.Ereuse
    PRICE_VERSION = StrictVersion('1.0')
    PRICE_CURRENCY = Currency.EUR
    """
    Official versions
    """

    def __init__(self, db: str = None) -> None:
        if not self.ORGANIZATION_NAME or not self.ORGANIZATION_TAX_ID:
            raise ValueError('You need to set the main organization parameters.')
        super().__init__(db)
