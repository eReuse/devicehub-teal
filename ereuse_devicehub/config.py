from distutils.version import StrictVersion
from itertools import chain
from typing import Set
from decouple import config

from teal.auth import TokenAuth
from teal.config import Config
from teal.enums import Currency
from teal.utils import import_resource

from ereuse_devicehub.resources import action, agent, deliverynote, inventory, \
    lot, tag, user
from ereuse_devicehub.resources.device import definitions
from ereuse_devicehub.resources.documents import documents
from ereuse_devicehub.resources.enums import PriceSoftware
from ereuse_devicehub.resources.versions import versions
from ereuse_devicehub.resources.licences import licences
from ereuse_devicehub.resources.metric import definitions as metric_def


class DevicehubConfig(Config):
    RESOURCE_DEFINITIONS = set(chain(import_resource(definitions),
                                     import_resource(action),
                                     import_resource(user),
                                     import_resource(tag),
                                     import_resource(agent),
                                     import_resource(lot),
                                     import_resource(deliverynote),
                                     import_resource(documents),
                                     import_resource(inventory),
                                     import_resource(versions),
                                     import_resource(licences),
                                     import_resource(metric_def),
                               ),)
    PASSWORD_SCHEMES = {'pbkdf2_sha256'}  # type: Set[str]
    DB_USER = config('DB_USER', 'dhub')
    DB_PASSWORD = config('DB_PASSWORD', 'ereuse')
    DB_HOST = config('DB_HOST', 'localhost')
    DB_DATABASE = config('DB_DATABASE', 'devicehub')
    SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{pw}@{host}/{db}'.format(
        user=DB_USER,
        pw=DB_PASSWORD,
        host=DB_HOST,
        db=DB_DATABASE,
    )  # type: str
    MIN_WORKBENCH = StrictVersion('11.0a1')  # type: StrictVersion
    """The minimum version of ereuse.org workbench that this devicehub
    accepts. we recommend not changing this value.
    """

    TMP_SNAPSHOTS = config('TMP_SNAPSHOTS', '/tmp/snapshots')
    TMP_LIVES = config('TMP_LIVES', '/tmp/lives')
    LICENCES = config('LICENCES', './licences.txt')
    """This var is for save a snapshots in json format when fail something"""
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

    """Admin email"""
    EMAIL_ADMIN = config('EMAIL_ADMIN', '')
