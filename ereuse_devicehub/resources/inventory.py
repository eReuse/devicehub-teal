from flask import current_app as app, jsonify
from marshmallow import Schema as MarshmallowSchema
from marshmallow.fields import Float, Nested, Str

from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.event.models import Rate
from ereuse_devicehub.resources.tag import Tag
from teal.marshmallow import IsType
from teal.query import Between, Equal, ILike, Or, Query
from teal.resource import Resource, Schema, View


class Inventory(Schema):
    pass


class RateQ(Query):
    rating = Between(Rate.rating, Float())
    appearance = Between(Rate.appearance, Float())
    functionality = Between(Rate.functionality, Float())


class TagQ(Query):
    id = Or(ILike(Tag.id), required=True)
    org = ILike(Tag.org)


class Filters(Query):
    type = Or(Equal(Device.type, Str(validate=IsType(Device.t))))
    model = ILike(Device.model)
    manufacturer = ILike(Device.manufacturer)
    serialNumber = ILike(Device.serial_number)
    rating = Nested(RateQ)  # todo db join
    tag = Nested(TagQ)  # todo db join


class InventoryView(View):
    class FindArgs(MarshmallowSchema):
        where = Nested(Filters, default={})

    def find(self, args):
        devices = Device.query.filter_by()
        inventory = {
            'devices': app.resources[Device.t].schema.dump()
        }
        return jsonify(inventory)


class InventoryDef(Resource):
    SCHEMA = Inventory
    VIEW = InventoryView
    AUTH = True
