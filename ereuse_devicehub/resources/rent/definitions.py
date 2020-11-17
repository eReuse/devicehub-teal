from ereuse_devicehub.resources.action import schemas
from teal.resource import Resource
from ereuse_devicehub.resources.rent.views import RentingView


class RentDef(Resource):
    VIEW = RentingView
    SCHEMA = schemas.Assigned
