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
    SCHEMA = Computer


class DesktopDef(ComputerDef):
    SCHEMA = Desktop


class LaptopDef(ComputerDef):
    SCHEMA = Laptop


class NetbookDef(ComputerDef):
    SCHEMA = Netbook


class ServerDef(ComputerDef):
    SCHEMA = Server


class MicrotowerDef(ComputerDef):
    SCHEMA = Microtower


class ComputerMonitorDef(DeviceDef):
    SCHEMA = ComputerMonitor


class ComponentDef(DeviceDef):
    SCHEMA = Component


class GraphicCardDef(ComponentDef):
    SCHEMA = GraphicCard


class DataStorageDef(ComponentDef):
    SCHEMA = DataStorage


class HardDriveDef(DataStorageDef):
    SCHEMA = HardDrive


class SolidStateDriveDef(DataStorageDef):
    SCHEMA = SolidStateDrive


class MotherboardDef(ComponentDef):
    SCHEMA = Motherboard


class NetworkAdapterDef(ComponentDef):
    SCHEMA = NetworkAdapter


class RamModuleDef(ComponentDef):
    SCHEMA = RamModule


class ProcessorDef(ComponentDef):
    SCHEMA = Processor
