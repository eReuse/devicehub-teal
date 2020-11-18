from typing import Callable, Iterable, Tuple
from ereuse_devicehub.resources.action import schemas
from teal.resource import Resource
from ereuse_devicehub.resources.assigned.views import AssignedView


class AssignedDef(Resource):
    VIEW = AssignedView
    SCHEMA = schemas.Assigned
