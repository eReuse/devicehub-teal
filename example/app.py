from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.devicehub import Devicehub

"""
Example app with minimal configuration.

Use this as a starting point.
"""


class MyConfig(DevicehubConfig):
    ORGANIZATION_NAME = 'My org'
    ORGANIZATION_TAX_ID = 'foo-bar'


app = Devicehub(MyConfig())
