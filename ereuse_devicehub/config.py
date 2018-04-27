from distutils.version import StrictVersion

from ereuse_devicehub.resources.device import ComponentDef, ComputerDef, DesktopDef, DeviceDef, \
    GraphicCardDef, HardDriveDef, LaptopDef, MicrotowerDef, MotherboardDef, NetbookDef, \
    NetworkAdapterDef, RamModuleDef, ServerDef
from ereuse_devicehub.resources.event import EventDef, SnapshotDef
from ereuse_devicehub.resources.user import UserDef
from teal.config import Config


class DevicehubConfig(Config):
    RESOURCE_DEFINITIONS = (
        DeviceDef, ComputerDef, DesktopDef, LaptopDef, NetbookDef, ServerDef, MicrotowerDef,
        ComponentDef, GraphicCardDef, HardDriveDef, MotherboardDef, NetworkAdapterDef,
        RamModuleDef, UserDef, EventDef, SnapshotDef
    )
    PASSWORD_SCHEMES = {'pbkdf2_sha256'}
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/dh-db1'
    MIN_WORKBENCH = StrictVersion('11.0')