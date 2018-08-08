import pathlib

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.lot import schemas
from ereuse_devicehub.resources.lot.views import LotView
from teal.resource import Converters, Resource


class LotDef(Resource):
    SCHEMA = schemas.Lot
    VIEW = LotView
    AUTH = True
    ID_CONVERTER = Converters.uuid

    def init_db(self, db: 'db.SQLAlchemy'):
        # Create functions
        with pathlib.Path(__file__).parent.joinpath('dag.sql').open() as f:
            sql = f.read()
            db.session.execute(sql)
