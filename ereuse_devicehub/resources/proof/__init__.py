from teal.resource import Converters, Resource

from ereuse_devicehub.resources.action import schemas
from ereuse_devicehub.resources.proof.views import ProofView


class ProofDef(Resource):
    SCHEMA = schemas.Proof
    VIEW = ProofView
    AUTH = True
    ID_CONVERTER = Converters.uuid


class ProofTransferDef(ProofDef):
    VIEW = None
    SCHEMA = schemas.ProofTransfer


class ProofDataWipeDef(ProofDef):
    VIEW = None
    SCHEMA = schemas.ProofDataWipe


class ProofFunction(ProofDef):
    VIEW = None
    SCHEMA = schemas.ProofFunction


class ProofReuse(ProofDef):
    VIEW = None
    SCHEMA = schemas.ProofReuse


class ProofRecycling(ProofDef):
    VIEW = None
    SCHEMA = schemas.ProofRecycling
