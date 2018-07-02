from distutils.version import StrictVersion
from typing import Set

from ereuse_devicehub.resources.device import CellphoneDef, ComponentDef, ComputerDef, \
    ComputerMonitorDef, DataStorageDef, DesktopDef, DeviceDef, DisplayDef, GraphicCardDef, \
    HardDriveDef, LaptopDef, MobileDef, MonitorDef, MotherboardDef, NetworkAdapterDef, \
    ProcessorDef, RamModuleDef, ServerDef, SmartphoneDef, SolidStateDriveDef, TabletDef, \
    TelevisionSetDef, SoundCardDef
from ereuse_devicehub.resources.event import AddDef, AggregateRateDef, AppRateDef, \
    BenchmarkDataStorageDef, BenchmarkDef, BenchmarkProcessorDef, BenchmarkProcessorSysbenchDef, \
    BenchmarkRamSysbenchDef, BenchmarkWithRateDef, EraseBasicDef, EraseSectorsDef, EventDef, \
    InstallDef, PhotoboxSystemRateDef, PhotoboxUserDef, RateDef, RemoveDef, SnapshotDef, StepDef, \
    StepRandomDef, StepZeroDef, StressTestDef, TestDataStorageDef, TestDef, WorkbenchRateDef
from ereuse_devicehub.resources.inventory import InventoryDef
from ereuse_devicehub.resources.tag import TagDef
from ereuse_devicehub.resources.user import OrganizationDef, UserDef
from teal.auth import TokenAuth
from teal.config import Config


class DevicehubConfig(Config):
    RESOURCE_DEFINITIONS = {
        DeviceDef, ComputerDef, DesktopDef, LaptopDef, ServerDef, MonitorDef, TelevisionSetDef,
        ComputerMonitorDef, ComponentDef, GraphicCardDef, DataStorageDef,
        SolidStateDriveDef, MobileDef, DisplayDef, SmartphoneDef, TabletDef, CellphoneDef,
        HardDriveDef, MotherboardDef, NetworkAdapterDef, RamModuleDef, ProcessorDef, SoundCardDef,
        UserDef,
        OrganizationDef, TagDef, EventDef, AddDef, RemoveDef, EraseBasicDef, EraseSectorsDef,
        StepDef, StepZeroDef, StepRandomDef, RateDef, AggregateRateDef, WorkbenchRateDef,
        PhotoboxUserDef, PhotoboxSystemRateDef, InstallDef, SnapshotDef, TestDef,
        TestDataStorageDef, StressTestDef, WorkbenchRateDef, InventoryDef, BenchmarkDef,
        BenchmarkDataStorageDef, BenchmarkWithRateDef, AppRateDef, BenchmarkProcessorDef,
        BenchmarkProcessorSysbenchDef, BenchmarkRamSysbenchDef
    }
    PASSWORD_SCHEMES = {'pbkdf2_sha256'}  # type: Set[str]
    SQLALCHEMY_DATABASE_URI = 'postgresql://dhub:ereuse@localhost/devicehub'  # type: str
    MIN_WORKBENCH = StrictVersion('11.0a1')  # type: StrictVersion
    """
    the minimum algorithm_version of ereuse.org workbench that this devicehub
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

    def __init__(self, db: str = None) -> None:
        if not self.ORGANIZATION_NAME or not self.ORGANIZATION_TAX_ID:
            raise ValueError('You need to set the main organization parameters.')
        super().__init__(db)
