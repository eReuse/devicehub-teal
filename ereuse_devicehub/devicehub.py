from typing import Type

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from teal.config import Config as ConfigClass
from teal.teal import Teal

from ereuse_devicehub.auth import Auth
from ereuse_devicehub.client import Client
from ereuse_devicehub.db import db
from ereuse_devicehub.dummy.dummy import Dummy
from ereuse_devicehub.resources.device.search import DeviceSearch


class Devicehub(Teal):
    test_client_class = Client
    Dummy = Dummy

    def __init__(self,
                 config: ConfigClass,
                 db: SQLAlchemy = db,
                 import_name=__package__,
                 static_url_path=None,
                 static_folder='static',
                 static_host=None,
                 host_matching=False,
                 subdomain_matching=False,
                 template_folder='templates',
                 instance_path=None,
                 instance_relative_config=False,
                 root_path=None,
                 Auth: Type[Auth] = Auth):
        super().__init__(config, db, import_name, static_url_path, static_folder, static_host,
                         host_matching, subdomain_matching, template_folder, instance_path,
                         instance_relative_config, root_path, Auth)
        self.dummy = Dummy(self)
        self.before_request(self.register_db_events_listeners)

    def register_db_events_listeners(self):
        """Registers the SQLAlchemy event listeners."""
        # todo can I make it with a global Session only?
        event.listen(db.session, 'before_commit', DeviceSearch.update_modified_devices)

    def _init_db(self):
        super()._init_db()
        DeviceSearch.set_all_devices_tokens_if_empty(self.db.session)
