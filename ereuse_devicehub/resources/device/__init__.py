from ereuse_devicehub.resources.device.schemas import Component, Computer, Desktop, Device, \
    GraphicCard, HardDrive, Laptop, Microtower, Motherboard, Netbook, NetworkAdapter, Processor, \
    RamModule, Server
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


class ComponentDef(DeviceDef):
    SCHEMA = Component


class GraphicCardDef(ComponentDef):
    SCHEMA = GraphicCard


class HardDriveDef(ComponentDef):
    SCHEMA = HardDrive


class MotherboardDef(ComponentDef):
    SCHEMA = Motherboard


class NetworkAdapterDef(ComponentDef):
    SCHEMA = NetworkAdapter


class RamModuleDef(ComponentDef):
    SCHEMA = RamModule


class ProcessorDef(ComponentDef):
    SCHEMA = Processor
