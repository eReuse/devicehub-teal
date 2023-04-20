from enum import Enum
from typing import Any

from marshmallow import post_load
from marshmallow.fields import DateTime, List, String
from marshmallow.schema import SchemaMeta

from ereuse_devicehub.resources import models as m
from ereuse_devicehub.teal.marshmallow import URL
from ereuse_devicehub.teal.resource import Schema


class UnitCodes(Enum):
    mbyte = '4L'
    mbps = 'E20'
    mhz = 'MHZ'
    gbyte = 'E34'
    ghz = 'A86'
    bit = 'A99'
    kgm = 'KGM'
    m = 'MTR'

    def __str__(self):
        return self.name


# The following SchemaMeta modifications allow us to generate
# documentation using our directive. This is their only purpose.
# Marshmallow's meta class removes variables from our defined
# classes, so we put some home made proxies in order to intercept
# those values and safe them in our classes.
# What we do is:
# 1. Make our ``Meta`` class be the superclass of Marshmallow's
#    SchemaMeta and provide a new that stores in class, so we
#    can save some vars.
# 2. Substitute SchemaMeta.get_declared_fields with our own method
#    that saves more variables.
# Then the directive in our docs/config.py file reads these variables
# generating the documentation.


class Meta(type):
    def __new__(cls, *args, **kw) -> Any:
        base_name = args[1][0].__name__
        y = super().__new__(cls, *args, **kw)
        y._base_class = base_name
        return y


SchemaMeta.__bases__ = (Meta,)


@classmethod
def get_declared_fields(mcs, klass, cls_fields, inherited_fields, dict_cls):
    klass._own = cls_fields
    klass._inherited = inherited_fields
    return dict_cls(inherited_fields + cls_fields)


SchemaMeta.get_declared_fields = get_declared_fields

_type_description = """The name of the type of Thing, 
like "Device" or "Receive". This is the same as JSON-LD ``@type``.

This field is required when submitting values
so Devicehub knows the type of object. Devicehub always returns this
value.
"""


class Thing(Schema):
    type = String(description=_type_description)
    same_as = List(URL(dump_only=True), dump_only=True, data_key='sameAs')
    updated = DateTime('iso', dump_only=True, description=m.Thing.updated.comment)
    created = DateTime('iso', dump_only=True, description=m.Thing.created.comment)

    @post_load
    def remove_type(self, data: dict):
        data.pop('type', None)
