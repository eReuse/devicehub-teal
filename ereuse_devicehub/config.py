from distutils.version import StrictVersion
from typing import Set

from ereuse_devicehub.resources.device import ComponentDef, ComputerDef, DataStorageDef, \
    DesktopDef, DeviceDef, GraphicCardDef, HardDriveDef, LaptopDef, MicrotowerDef, \
    MotherboardDef, NetbookDef, NetworkAdapterDef, ProcessorDef, RamModuleDef, ServerDef, \
    SolidStateDriveDef
from ereuse_devicehub.resources.event import AddDef, AggregateRateDef, EventDef, InstallDef, \
    PhotoboxSystemRateDef, PhotoboxUserDef, RateDef, RemoveDef, SnapshotDef, StepDef, \
    StepRandomDef, StepZeroDef, TestDataStorageDef, TestDef, WorkbenchRateDef, EraseBasicDef, \
    EraseSectorsDef
from ereuse_devicehub.resources.tag import TagDef
from ereuse_devicehub.resources.user import OrganizationDef, UserDef
from teal.config import Config


class DevicehubConfig(Config):
    RESOURCE_DEFINITIONS = {
        DeviceDef, ComputerDef, DesktopDef, LaptopDef, NetbookDef, ServerDef,
        MicrotowerDef, ComponentDef, GraphicCardDef, DataStorageDef, SolidStateDriveDef,
        HardDriveDef, MotherboardDef, NetworkAdapterDef, RamModuleDef, ProcessorDef, UserDef,
        OrganizationDef, TagDef, EventDef, AddDef, RemoveDef, EraseBasicDef, EraseSectorsDef,
        StepDef, StepZeroDef, StepRandomDef, RateDef, AggregateRateDef, WorkbenchRateDef,
        PhotoboxUserDef, PhotoboxSystemRateDef, InstallDef, SnapshotDef, TestDef,
        TestDataStorageDef, WorkbenchRateDef
    }
    PASSWORD_SCHEMES = {'pbkdf2_sha256'}  # type: Set[str]
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/dh-db1'  # type: str
    MIN_WORKBENCH = StrictVersion('11.0')  # type: StrictVersion
    """
    The minimum algorithm_version of eReuse.org Workbench that this Devicehub
    accepts. We recommend not changing this value.
    """
    ORGANIZATION_NAME = None  # type: str
    ORGANIZATION_TAX_ID = None  # type: str
    """
    The organization using this Devicehub.
    
    It is used by default, for example, when creating tags.
    """

    def __init__(self, db: str = None) -> None:
        if not self.ORGANIZATION_NAME or not self.ORGANIZATION_TAX_ID:
            raise ValueError('You need to set the main organization parameters.')
        super().__init__(db)
