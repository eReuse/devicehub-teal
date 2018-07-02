from ereuse_devicehub.resources.device.schemas import Cellphone, Component, Computer, \
    ComputerMonitor, DataStorage, Desktop, Device, Display, GraphicCard, HardDrive, Laptop, Mobile, \
    Monitor, Motherboard, NetworkAdapter, Processor, RamModule, Server, Smartphone, \
    SolidStateDrive, SoundCard, Tablet, TelevisionSet
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


class ServerDef(ComputerDef):
    VIEW = None
    SCHEMA = Server


class MonitorDef(DeviceDef):
    VIEW = None
    SCHEMA = Monitor


class ComputerMonitorDef(MonitorDef):
    VIEW = None
    SCHEMA = ComputerMonitor


class TelevisionSetDef(MonitorDef):
    VIEW = None
    SCHEMA = TelevisionSet


class MobileDef(DeviceDef):
    VIEW = None
    SCHEMA = Mobile


class SmartphoneDef(MobileDef):
    VIEW = None
    SCHEMA = Smartphone


class TabletDef(MobileDef):
    VIEW = None
    SCHEMA = Tablet


class CellphoneDef(MobileDef):
    VIEW = None
    SCHEMA = Cellphone


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


class SoundCardDef(ComponentDef):
    VIEW = None
    SCHEMA = SoundCard


class DisplayDef(ComponentDef):
    VIEW = None
    SCHEMA = Display
