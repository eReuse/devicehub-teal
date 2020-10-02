from decouple import config

from ereuse_tag.auth import Auth
from ereuse_tag.config import TagsConfig
from ereuse_tag.db import db
from teal.teal import Teal


class DeviceTagConf(TagsConfig):
    TAG_PROVIDER_ID = 'DT'
    TAG_HASH_SALT = '$6f/Wspgaswc1xJq5xj'
    DB_USER = config('DB_USER', 'dtag')
    DB_PASSWORD = config('DB_PASSWORD', 'ereuse')
    DB_HOST = config('DB_HOST', 'localhost')
    DB_DATABASE = config('DB_DATABASE', 'tags')
    SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{pw}@{host}/{db}'.format(
        user=DB_USER, pw=DB_PASSWORD, host=DB_HOST, db=DB_DATABASE)  #type: str
    DEVICEHUBS = {
        '899c794e-1737-4cea-9232-fdc507ab7106': 'https://api.dh.usody.net/dbtest',
        '9f564863-2d28-4b69-a541-a08c5b34d422': 'https://api.testing.usody.com/usodybeta',
    }


application = Teal(config=DeviceTagConf(), db=db, Auth=Auth)
