from typing import Type

from flask_sqlalchemy import SQLAlchemy

from ereuse_devicehub.auth import Auth
from ereuse_devicehub.client import Client
from ereuse_devicehub.db import db
from teal.config import Config as ConfigClass
from teal.teal import Teal


class Devicehub(Teal):
    test_client_class = Client

    def __init__(self, config: ConfigClass,
                 db: SQLAlchemy = db,
                 import_name=__package__,
                 static_path=None,
                 static_url_path=None,
                 static_folder='static',
                 template_folder='templates',
                 instance_path=None,
                 instance_relative_config=False,
                 root_path=None,
                 Auth: Type[Auth] = Auth):
        super().__init__(config, db, import_name, static_path, static_url_path, static_folder,
                         template_folder, instance_path, instance_relative_config, root_path, Auth)
