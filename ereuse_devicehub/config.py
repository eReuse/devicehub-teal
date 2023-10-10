from distutils.version import StrictVersion
from itertools import chain

from decouple import config

from ereuse_devicehub.resources import (
    action,
    agent,
    deliverynote,
    inventory,
    lot,
    tag,
    user,
)
from ereuse_devicehub.resources.device import definitions
from ereuse_devicehub.resources.did import did
from ereuse_devicehub.resources.documents import documents
from ereuse_devicehub.resources.enums import PriceSoftware
from ereuse_devicehub.resources.licences import licences
from ereuse_devicehub.resources.metric import definitions as metric_def
from ereuse_devicehub.resources.tradedocument import definitions as tradedocument
from ereuse_devicehub.resources.versions import versions
from ereuse_devicehub.teal.auth import TokenAuth
from ereuse_devicehub.teal.config import Config
from ereuse_devicehub.teal.enums import Currency
from ereuse_devicehub.teal.utils import import_resource


class DevicehubConfig(Config):
    RESOURCE_DEFINITIONS = set(
        chain(
            import_resource(definitions),
            import_resource(action),
            import_resource(user),
            import_resource(tag),
            import_resource(did),
            import_resource(agent),
            import_resource(lot),
            import_resource(deliverynote),
            import_resource(documents),
            import_resource(tradedocument),
            import_resource(inventory),
            import_resource(versions),
            import_resource(licences),
            import_resource(metric_def),
        ),
    )
    PASSWORD_SCHEMES = {'pbkdf2_sha256'}
    SECRET_KEY = config('SECRET_KEY')
    DB_USER = config('DB_USER', 'dhub')
    DB_PASSWORD = config('DB_PASSWORD', 'ereuse')
    DB_HOST = config('DB_HOST', 'localhost')
    DB_DATABASE = config('DB_DATABASE', 'devicehub')
    DB_SCHEMA = config('DB_SCHEMA', 'dbtest')
    SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{pw}@{host}/{db}'.format(
        user=DB_USER,
        pw=DB_PASSWORD,
        host=DB_HOST,
        db=DB_DATABASE,
    )  # type: str
    SCHEMA = config('SCHEMA', 'dbtest')
    HOST = config('HOST', 'localhost')
    API_HOST = config('API_HOST', 'localhost')
    MIN_WORKBENCH = StrictVersion('11.0a1')  # type: StrictVersion
    """The minimum version of ereuse.org workbench that this devicehub
    accepts. we recommend not changing this value.
    """
    SCHEMA_WORKBENCH = ["1.0.0"]

    TMP_SNAPSHOTS = config('TMP_SNAPSHOTS', '/tmp/snapshots')
    TMP_LIVES = config('TMP_LIVES', '/tmp/lives')
    LICENCES = config('LICENCES', './licences.txt')
    """This var is for save a snapshots in json format when fail something"""
    API_DOC_CONFIG_TITLE = 'Devicehub'
    API_DOC_CONFIG_VERSION = '0.2'
    API_DOC_CONFIG_COMPONENTS = {'securitySchemes': {'bearerAuth': TokenAuth.API_DOCS}}
    API_DOC_CLASS_DISCRIMINATOR = 'type'

    PRICE_SOFTWARE = PriceSoftware.Ereuse
    PRICE_VERSION = StrictVersion('1.0')
    PRICE_CURRENCY = Currency.EUR
    """Official versions."""

    """Admin email"""
    EMAIL_ADMIN = config('EMAIL_ADMIN', '')
    EMAIL_DEMO = config('EMAIL_DEMO', 'hello@usody.com')

    """Definition of path where save the documents of customers"""
    PATH_DOCUMENTS_STORAGE = config('PATH_DOCUMENTS_STORAGE', '/tmp/')
    JWT_PASS = config('JWT_PASS', '')

    MAIL_SERVER = config('MAIL_SERVER', '')
    MAIL_USERNAME = config('MAIL_USERNAME', '')
    MAIL_PASSWORD = config('MAIL_PASSWORD', '')
    MAIL_PORT = config('MAIL_PORT', 587)
    MAIL_USE_TLS = config('MAIL_USE_TLS', True)
    MAIL_DEFAULT_SENDER = config('MAIL_DEFAULT_SENDER', '')
    API_DLT = config('API_DLT', None)
    API_DLT_TOKEN = config('API_DLT_TOKEN', None)
    ID_FEDERATED = config('ID_FEDERATED', None)
    URL_MANUALS = config('URL_MANUALS', None)

    """Definition of oauth jwt details."""
    OAUTH2_JWT_ENABLED = config('OAUTH2_JWT_ENABLED', False)
    OAUTH2_JWT_ISS = config('OAUTH2_JWT_ISS', '')
    OAUTH2_JWT_KEY = config('OAUTH2_JWT_KEY', None)
    OAUTH2_JWT_ALG = config('OAUTH2_JWT_ALG', 'HS256')

    if API_DLT:
        API_DLT = API_DLT.strip("/")
