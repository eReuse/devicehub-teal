import ereuse_devicehub.ereuse_utils
from flask.json import JSONEncoder as FlaskJSONEncoder
from sqlalchemy.ext.baked import Result
from sqlalchemy.orm import Query


class TealJSONEncoder(ereuse_devicehub.ereuse_utils.JSONEncoder, FlaskJSONEncoder):
    def default(self, obj):
        if isinstance(obj, (Result, Query)):
            return tuple(obj)
        return super().default(obj)
