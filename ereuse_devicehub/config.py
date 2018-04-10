from ereuse_devicehub.resources.device import DeviceDef
from teal.config import Config


class DevicehubConfig(Config):
    RESOURCE_DEFINITIONS = (DeviceDef,)
