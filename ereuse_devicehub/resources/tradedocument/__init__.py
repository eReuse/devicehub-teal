from teal.resource import Converters, Resource

from ereuse_devicehub.resources.tradedocument import schemas
from ereuse_devicehub.resources.tradedocument.views import DocumentView 

class TradeDocumentDef(Resource):
    SCHEMA = schemas.Document
    VIEW = DocumentView
    AUTH = True
    ID_CONVERTER = Converters.string
