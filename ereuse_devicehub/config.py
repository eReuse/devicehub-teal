from distutils.version import StrictVersion
from itertools import chain
from typing import Set

from teal.auth import TokenAuth
from teal.config import Config
from teal.enums import Currency
from teal.utils import import_resource

from ereuse_devicehub.resources import agent, event, inventory, lot, tag, user
from ereuse_devicehub.resources.device import definitions
from ereuse_devicehub.resources.documents import documents
from ereuse_devicehub.resources.enums import PriceSoftware, RatingSoftware


class DevicehubConfig(Config):
    RESOURCE_DEFINITIONS = set(chain(import_resource(definitions),
                                     import_resource(event),
                                     import_resource(user),
                                     import_resource(tag),
                                     import_resource(agent),
                                     import_resource(lot),
                                     import_resource(documents),
                                     import_resource(inventory)),
                               )
    PASSWORD_SCHEMES = {'pbkdf2_sha256'}  # type: Set[str]
    SQLALCHEMY_DATABASE_URI = 'postgresql://dhub:ereuse@localhost/devicehub'  # type: str
    MIN_WORKBENCH = StrictVersion('11.0a1')  # type: StrictVersion
    """
    the minimum version of ereuse.org workbench that this devicehub
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

    WORKBENCH_RATE_SOFTWARE = RatingSoftware.ECost
    WORKBENCH_RATE_VERSION = StrictVersion('1.0')
    PHOTOBOX_RATE_SOFTWARE = RatingSoftware.ECost
    PHOTOBOX_RATE_VERSION = StrictVersion('1.0')
    """
    Official versions for WorkbenchRate and PhotoboxRate
    """
    PRICE_SOFTWARE = PriceSoftware.Ereuse
    PRICE_VERSION = StrictVersion('1.0')
    PRICE_CURRENCY = Currency.EUR
    """
    Official versions
    """
