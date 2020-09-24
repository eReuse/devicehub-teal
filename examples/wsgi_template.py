"""
[Testing] Apache python WSGI to a Devicehub app with a dispatcher.
"""
from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.dispatchers import PathDispatcher

class MyConfig(DevicehubConfig):
    SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{password}@{host}/{database}'


application = PathDispatcher(config_cls=MyConfig)
