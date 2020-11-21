from ereuse_devicehub.resources.action import schemas
from teal.resource import Resource
from ereuse_devicehub.resources.allocate.views import AllocateView, DeallocateView


class AllocateDef(Resource):
    VIEW = AllocateView
    SCHEMA = schemas.Allocate
    AUTH = True

class DeallocateDef(Resource):
    VIEW = DeallocateView
    SCHEMA = schemas.Deallocate
    AUTH = True
