from enum import Enum

from marshmallow import post_load
from marshmallow.fields import DateTime, List, String
from teal.marshmallow import URL
from teal.resource import Schema

from ereuse_devicehub.resources import models as m


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
    same_as = List(URL(dump_only=True), dump_only=True, data_key='sameAs')
    updated = DateTime('iso', dump_only=True, description=m.Thing.updated.comment.strip())
    created = DateTime('iso', dump_only=True, description=m.Thing.created.comment.strip())

    @post_load
    def remove_type(self, data: dict):
        data.pop('type', None)
