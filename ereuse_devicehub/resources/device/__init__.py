from ereuse_devicehub.resources.device import schemas
from ereuse_devicehub.resources.device.views import DeviceView
from teal.resource import Converters, Resource


class DeviceDef(Resource):
    SCHEMA = schemas.Device
    VIEW = DeviceView
    ID_CONVERTER = Converters.int
    AUTH = True


class ComputerDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Computer


class DesktopDef(ComputerDef):
    VIEW = None
    SCHEMA = schemas.Desktop


class LaptopDef(ComputerDef):
    VIEW = None
    SCHEMA = schemas.Laptop


class ServerDef(ComputerDef):
    VIEW = None
    SCHEMA = schemas.Server


class MonitorDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Monitor


class ComputerMonitorDef(MonitorDef):
    VIEW = None
    SCHEMA = schemas.ComputerMonitor


class TelevisionSetDef(MonitorDef):
    VIEW = None
    SCHEMA = schemas.TelevisionSet


class MobileDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Mobile


class SmartphoneDef(MobileDef):
    VIEW = None
    SCHEMA = schemas.Smartphone


class TabletDef(MobileDef):
    VIEW = None
    SCHEMA = schemas.Tablet


class CellphoneDef(MobileDef):
    VIEW = None
    SCHEMA = schemas.Cellphone


class ComponentDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Component


class GraphicCardDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.GraphicCard


class DataStorageDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.DataStorage


class HardDriveDef(DataStorageDef):
    VIEW = None
    SCHEMA = schemas.HardDrive


class SolidStateDriveDef(DataStorageDef):
    VIEW = None
    SCHEMA = schemas.SolidStateDrive


class MotherboardDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.Motherboard


class NetworkAdapterDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.NetworkAdapter


class RamModuleDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.RamModule


class ProcessorDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.Processor


class SoundCardDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.SoundCard


class DisplayDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.Display
