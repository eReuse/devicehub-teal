"""
[Testing] Apache python WSGI to a Devicehub app with a dispatcher.
"""
from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.dispatchers import PathDispatcher

application = PathDispatcher(config_cls=DevicehubConfig)
