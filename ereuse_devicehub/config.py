from distutils.version import StrictVersion
from itertools import chain
from typing import Set

from teal.auth import TokenAuth
from teal.config import Config
from teal.enums import Currency
from teal.utils import import_resource

from ereuse_devicehub.resources import action, agent, deliverynote, inventory, lot, tag, user
from ereuse_devicehub.resources.device import definitions
from ereuse_devicehub.resources.documents import documents
from ereuse_devicehub.resources.enums import PriceSoftware


class DevicehubConfig(Config):
    RESOURCE_DEFINITIONS = set(chain(import_resource(definitions),
                                     import_resource(action),
                                     import_resource(user),
                                     import_resource(tag),
                                     import_resource(agent),
                                     import_resource(lot),
                                     import_resource(deliverynote),
                                     import_resource(proof),
                                     import_resource(documents),
                                     import_resource(inventory)),
                               )
    PASSWORD_SCHEMES = {'pbkdf2_sha256'}  # type: Set[str]
    SQLALCHEMY_DATABASE_URI = 'postgresql://dhub:ereuse@localhost/devicehub'  # type: str
    MIN_WORKBENCH = StrictVersion('11.0a1')  # type: StrictVersion
    """The minimum version of ereuse.org workbench that this devicehub
    accepts. we recommend not changing this value.
    """
    API_DOC_CONFIG_TITLE = 'Devicehub'
    API_DOC_CONFIG_VERSION = '0.2'
    API_DOC_CONFIG_COMPONENTS = {
        'securitySchemes': {
            'bearerAuth': TokenAuth.API_DOCS
        }
    }
    API_DOC_CLASS_DISCRIMINATOR = 'type'

    PRICE_SOFTWARE = PriceSoftware.Ereuse
    PRICE_VERSION = StrictVersion('1.0')
    PRICE_CURRENCY = Currency.EUR
    """Official versions."""
