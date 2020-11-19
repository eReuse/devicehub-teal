from typing import Callable, Iterable, Tuple
from ereuse_devicehub.resources.action import schemas
from teal.resource import Resource
from ereuse_devicehub.resources.allocate.views import AllocateView


class AssignedDef(Resource):
    VIEW = AllocateView
    SCHEMA = schemas.Allocate

