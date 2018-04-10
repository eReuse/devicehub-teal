from ereuse_devicehub.resources.event.views import EventView
from teal.resource import Resource


class EventDef(Resource):
    SCHEMA = None
    VIEW = EventView
