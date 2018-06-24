from flask import current_app, current_app as app, jsonify
from flask_sqlalchemy import Pagination
from marshmallow import Schema as MarshmallowSchema
from marshmallow.fields import Float, Integer, Nested, Str
from marshmallow.validate import Range
from sqlalchemy import Column

from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.event.models import Rate
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.tag import Tag
from teal.query import Between, FullTextSearch, ILike, Join, Or, Query, Sort, SortField
from teal.resource import Resource, View


class Inventory(Thing):
    pass


class RateQ(Query):
    rating = Between(Rate.rating, Float())
    appearance = Between(Rate.appearance, Float())
    functionality = Between(Rate.functionality, Float())


class TagQ(Query):
    id = Or(ILike(Tag.id), required=True)
    org = ILike(Tag.org)


class OfType(Str):
    def __init__(self, column: Column, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.column = column

    def _deserialize(self, value, attr, data):
        v = super()._deserialize(value, attr, data)
        return self.column.in_(current_app.resources[v].subresources_types)


class Filters(Query):
    type = Or(OfType(Device.type))
    model = ILike(Device.model)
    manufacturer = ILike(Device.manufacturer)
    serialNumber = ILike(Device.serial_number)
    rating = Join(Device.id == Rate.device_id, RateQ)
    tag = Join(Device.id == Tag.id, TagQ)


class Sorting(Sort):
    created = SortField(Device.created)


class InventoryView(View):
    class FindArgs(MarshmallowSchema):
        search = FullTextSearch()  # todo Develop this. See more at docs/inventory.
        filter = Nested(Filters, missing=[])
        sort = Nested(Sorting, missing=[Device.created.desc()])
        page = Integer(validate=Range(min=1), missing=1)

    def get(self, id):
        """Inventory view
        ---
        description: Supports the inventory view of ``devicehub-client``; returns
                     all the devices, groups and widgets of this Devicehub instance.
        responses:
          200:
            description: The inventory.
            schema:
              type: object
              properties:
                devices:
                  type: array
                  items:
                    $ref: '#/definitions/Device'
                pagination:
                  type: object
                  properties:
                    page:
                      type: integer
                      minimum: 0
                    perPage:
                      type: integer
                      minimum: 0
                    total:
                      type: integer
                      minimum: 0
        """
        # todo .format(yaml.load(schema2parameters(self.FindArgs, default_in='path', name='path')))
        return super().get(id)

    def find(self, args: dict):
        """See :meth:`.get` above."""
        devices = Device.query \
            .filter(*args['filter']) \
            .order_by(*args['sort']) \
            .paginate(page=args['page'], per_page=30)  # type: Pagination
        inventory = {
            'devices': app.resources[Device.t].schema.dump(devices.items, many=True),
            'groups': [],
            'widgets': {},
            'pagination': {
                'page': devices.page,
                'perPage': devices.per_page,
                'total': devices.total,
            }
        }
        return jsonify(inventory)


class InventoryDef(Resource):
    SCHEMA = Inventory
    VIEW = InventoryView
    AUTH = True
