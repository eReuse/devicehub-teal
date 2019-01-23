from threading import Lock

import sqlalchemy as sa
import werkzeug.exceptions
from werkzeug import wsgi

import ereuse_devicehub.config
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.inventory import Inventory


class PathDispatcher:
    NOT_FOUND = werkzeug.exceptions.NotFound()
    INV = Inventory

    def __init__(self, config_cls=ereuse_devicehub.config.DevicehubConfig) -> None:
        self.lock = Lock()
        self.instances = {}
        self.CONFIG = config_cls
        self.engine = sa.create_engine(self.CONFIG.SQLALCHEMY_DATABASE_URI)
        with self.lock:
            self.instantiate()
        if not self.instances:
            raise ValueError('There are no Devicehub instances! Please, execute `dh init-db`.')
        self.one_app = next(iter(self.instances.values()))

    def __call__(self, environ, start_response):
        if wsgi.get_path_info(environ).startswith('/users'):
            # Not nice solution but it works well for now
            # Return any app, as all apps can handle login
            return self.call(self.one_app, environ, start_response)
        inventory = wsgi.pop_path_info(environ)
        with self.lock:
            if inventory not in self.instances:
                self.instantiate()
        app = self.instances.get(inventory, self.NOT_FOUND)
        return self.call(app, environ, start_response)

    @staticmethod
    def call(app, environ, start_response):
        return app(environ, start_response)

    def instantiate(self):
        sel = sa.select([self.INV.id]).where(self.INV.id.notin_(self.instances.keys()))
        for row in self.engine.execute(sel):
            self.instances[row.id] = Devicehub(inventory=row.id)
