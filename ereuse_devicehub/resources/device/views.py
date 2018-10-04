import datetime

import marshmallow
from flask import current_app as app, render_template, request
from flask.json import jsonify
from flask_sqlalchemy import Pagination
from marshmallow import fields as f, validate as v
from teal import query
from teal.cache import cache
from teal.resource import View

from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.resources import search
from ereuse_devicehub.resources.device.models import Device, Manufacturer
from ereuse_devicehub.resources.device.search import DeviceSearch
from ereuse_devicehub.resources.event.models import Rate
from ereuse_devicehub.resources.tag.model import Tag


class OfType(f.Str):
    def __init__(self, column: db.Column, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.column = column

    def _deserialize(self, value, attr, data):
        v = super()._deserialize(value, attr, data)
        return self.column.in_(app.resources[v].subresources_types)


class RateQ(query.Query):
    rating = query.Between(Rate.rating, f.Float())
    appearance = query.Between(Rate.appearance, f.Float())
    functionality = query.Between(Rate.functionality, f.Float())


class TagQ(query.Query):
    id = query.Or(query.ILike(Tag.id), required=True)
    org = query.ILike(Tag.org)


class Filters(query.Query):
    type = query.Or(OfType(Device.type))
    model = query.ILike(Device.model)
    manufacturer = query.ILike(Device.manufacturer)
    serialNumber = query.ILike(Device.serial_number)
    rating = query.Join(Device.id == Rate.device_id, RateQ)
    tag = query.Join(Device.id == Tag.id, TagQ)


class Sorting(query.Sort):
    created = query.SortField(Device.created)


class DeviceView(View):
    class FindArgs(marshmallow.Schema):
        search = f.Str()
        filter = f.Nested(Filters, missing=[])
        sort = f.Nested(Sorting, missing=[])
        page = f.Integer(validate=v.Range(min=1), missing=1)

    def get(self, id):
        """
        Devices view
        ---
        description: Gets a device or multiple devices.
        parameters:
          - name: id
            type: integer
            in: path
            description: The identifier of the device.
        responses:
          200:
            description: The device or devices.
        """
        return super().get(id)

    def one(self, id: int):
        """Gets one device."""
        if not request.authorization:
            return self.one_public(id)
        else:
            return self.one_private(id)

    def one_public(self, id: int):
        device = Device.query.filter_by(id=id).one()
        return render_template('devices/layout.html', device=device)

    @auth.Auth.requires_auth
    def one_private(self, id: int):
        device = Device.query.filter_by(id=id).one()
        return self.schema.jsonify(device)

    @auth.Auth.requires_auth
    def find(self, args: dict):
        """Gets many devices."""
        search_p = args.get('search', None)
        query = Device.query
        if search_p:
            properties = DeviceSearch.properties
            tags = DeviceSearch.tags
            query = query.join(DeviceSearch).filter(
                search.Search.match(properties, search_p) | search.Search.match(tags, search_p)
            ).order_by(
                search.Search.rank(properties, search_p) + search.Search.rank(tags, search_p)
            )
        query = query.filter(*args['filter']).order_by(*args['sort'])
        devices = query.paginate(page=args['page'], per_page=30)  # type: Pagination
        ret = {
            'items': self.schema.dump(devices.items, many=True, nested=1),
            # todo pagination should be in Header like github
            # https://developer.github.com/v3/guides/traversing-with-pagination/
            'pagination': {
                'page': devices.page,
                'perPage': devices.per_page,
                'total': devices.total
            }
        }
        return jsonify(ret)


class ManufacturerView(View):
    class FindArgs(marshmallow.Schema):
        name = marshmallow.fields.Str(required=True,
                                      # Disallow like operators
                                      validate=lambda x: '%' not in x and '_' not in x)

    @cache(datetime.timedelta(days=1))
    def find(self, args: dict):
        name = args['name']
        manufacturers = Manufacturer.query \
            .filter(Manufacturer.name.ilike(name + '%')) \
            .paginate(page=1, per_page=6)  # type: Pagination
        return jsonify(
            items=app.resources[Manufacturer.t].schema.dump(
                manufacturers.items,
                many=True,
                nested=1
            )
        )
