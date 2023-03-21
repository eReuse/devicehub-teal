from ereuse_devicehub.resources.tradedocument import schemas
from ereuse_devicehub.resources.tradedocument.views import TradeDocumentView
from ereuse_devicehub.teal.resource import Converters, Resource


class TradeDocumentDef(Resource):
    SCHEMA = schemas.TradeDocument
    VIEW = TradeDocumentView
    AUTH = True
    ID_CONVERTER = Converters.string
