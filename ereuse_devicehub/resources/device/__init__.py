from ereuse_devicehub.resources.device.schemas import Device
from ereuse_devicehub.resources.device.views import DeviceView
from teal.resource import Resource, Converters


class DeviceDef(Resource):
    SCHEMA = Device
    VIEW = DeviceView
    ID_CONVERTER = Converters.int
