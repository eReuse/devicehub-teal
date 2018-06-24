from ereuse_devicehub.resources.device.schemas import Component, Computer, ComputerMonitor, \
    DataStorage, Desktop, Device, GraphicCard, HardDrive, Laptop, Microtower, Motherboard, Netbook, \
    NetworkAdapter, Processor, RamModule, Server, SolidStateDrive
from ereuse_devicehub.resources.device.views import DeviceView
from teal.resource import Converters, Resource


class DeviceDef(Resource):
    SCHEMA = Device
    VIEW = DeviceView
    ID_CONVERTER = Converters.int
    AUTH = True


class ComputerDef(DeviceDef):
    VIEW = None
    SCHEMA = Computer


class DesktopDef(ComputerDef):
    VIEW = None
    SCHEMA = Desktop


class LaptopDef(ComputerDef):
    VIEW = None
    SCHEMA = Laptop


class NetbookDef(ComputerDef):
    VIEW = None
    SCHEMA = Netbook


class ServerDef(ComputerDef):
    VIEW = None
    SCHEMA = Server


class MicrotowerDef(ComputerDef):
    VIEW = None
    SCHEMA = Microtower


class ComputerMonitorDef(DeviceDef):
    VIEW = None
    SCHEMA = ComputerMonitor


class ComponentDef(DeviceDef):
    VIEW = None
    SCHEMA = Component


class GraphicCardDef(ComponentDef):
    VIEW = None
    SCHEMA = GraphicCard


class DataStorageDef(ComponentDef):
    VIEW = None
    SCHEMA = DataStorage


class HardDriveDef(DataStorageDef):
    VIEW = None
    SCHEMA = HardDrive


class SolidStateDriveDef(DataStorageDef):
    VIEW = None
    SCHEMA = SolidStateDrive


class MotherboardDef(ComponentDef):
    VIEW = None
    SCHEMA = Motherboard


class NetworkAdapterDef(ComponentDef):
    VIEW = None
    SCHEMA = NetworkAdapter


class RamModuleDef(ComponentDef):
    VIEW = None
    SCHEMA = RamModule


class ProcessorDef(ComponentDef):
    VIEW = None
    SCHEMA = Processor
