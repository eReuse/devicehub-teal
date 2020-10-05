import json

from ereuse_tag.auth import Auth
from ereuse_tag.config import TagsConfig
from ereuse_tag.db import db
from teal.teal import Teal
from teal.auth import TokenAuth
from decouple import config


class DeviceTagConf(TagsConfig):
    TAG_PROVIDER_ID = config('TAG_PROVIDER_ID')
    TAG_HASH_SALT = config('TAG_HASH_SALT')
    DEVICEHUBS = json.loads(config('DEVICEHUBS'))
    API_DOC_CONFIG_TITLE = 'Tags'
    API_DOC_CONFIG_VERSION = '0.1'
    API_DOC_CONFIG_COMPONENTS = {
        'securitySchemes': {
            'bearerAuth': TokenAuth.API_DOCS
        }
    }
    API_DOC_CLASS_DISCRIMINATOR = 'type'


application = Teal(config=DeviceTagConf(), db=db, Auth=Auth)
