from distutils.version import StrictVersion

from ereuse_devicehub.resources.device import ComponentDef, ComputerDef, DesktopDef, DeviceDef, \
    GraphicCardDef, HardDriveDef, LaptopDef, MicrotowerDef, MotherboardDef, NetbookDef, \
    NetworkAdapterDef, ProcessorDef, RamModuleDef, ServerDef
from ereuse_devicehub.resources.event import AddDef, EventDef, RemoveDef, SnapshotDef, TestDef, \
    TestHardDriveDef
from ereuse_devicehub.resources.tag import TagDef
from ereuse_devicehub.resources.user import OrganizationDef, UserDef
from teal.config import Config


class DevicehubConfig(Config):
    RESOURCE_DEFINITIONS = (
        DeviceDef, ComputerDef, DesktopDef, LaptopDef, NetbookDef, ServerDef,
        MicrotowerDef, ComponentDef, GraphicCardDef, HardDriveDef, MotherboardDef,
        NetworkAdapterDef, RamModuleDef, ProcessorDef, UserDef, OrganizationDef, TagDef, EventDef,
        AddDef, RemoveDef, SnapshotDef, TestDef, TestHardDriveDef
    )
    PASSWORD_SCHEMES = {'pbkdf2_sha256'}
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/dh-db1'
    MIN_WORKBENCH = StrictVersion('11.0')
    """
    The minimum version of eReuse.org Workbench that this Devicehub
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
