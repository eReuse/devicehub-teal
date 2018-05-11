from enum import Enum

from marshmallow import post_load
from marshmallow.fields import DateTime, List, String, URL

from ereuse_devicehub.marshmallow import NestedOn
from teal.resource import Schema


class UnitCodes(Enum):
    mbyte = '4L'
    mbps = 'E20'
    mhz = 'MHZ'
    gbyte = 'E34'
    ghz = 'A86'
    bit = 'A99'
    kgm = 'KGM'
    m = 'MTR'


class Thing(Schema):
    type = String(description='Only required when it is nested.')
    url = URL(dump_only=True, description='The URL of the resource.')
    same_as = List(URL(dump_only=True), dump_only=True, data_key='sameAs')
    updated = DateTime('iso', dump_only=True)
    created = DateTime('iso', dump_only=True)
    author = NestedOn('User', dump_only=True, exclude=('token',))

    @post_load
    def remove_type(self, data: dict):
        data.pop('type', None)
