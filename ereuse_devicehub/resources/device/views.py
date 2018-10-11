import datetime
import itertools
from collections import OrderedDict

import marshmallow
from flask import current_app as app, render_template, request
from flask.json import jsonify
from flask_sqlalchemy import Pagination
from marshmallow import fields, fields as f, validate as v
from sqlalchemy.orm import aliased
from teal import query
from teal.cache import cache
from teal.resource import View

from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.resources import search
from ereuse_devicehub.resources.device.definitions import ComponentDef
from ereuse_devicehub.resources.device.models import Component, Computer, Device, Manufacturer, \
    RamModule, Processor, DataStorage
from ereuse_devicehub.resources.device.search import DeviceSearch
from ereuse_devicehub.resources.event.models import Rate, Event
from ereuse_devicehub.resources.lot.models import Lot, LotDevice
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


class LotQ(query.Query):
    id = query.Or(query.QueryField(Lot.descendantsq, fields.UUID()))


class Filters(query.Query):
    _parent = aliased(Computer)
    _device_inside_lot = (Device.id == LotDevice.device_id) & (Lot.id == LotDevice.lot_id)
    _component_inside_lot_through_parent = (Device.id == Component.id) \
                                           & (Component.parent_id == _parent.id) \
                                           & (_parent.id == LotDevice.device_id)

    type = query.Or(OfType(Device.type))
    model = query.ILike(Device.model)
    manufacturer = query.ILike(Device.manufacturer)
    serialNumber = query.ILike(Device.serial_number)
    rating = query.Join(Device.id == Rate.device_id, RateQ)
    tag = query.Join(Device.id == Tag.device_id, TagQ)
    lot = query.Join(_device_inside_lot | _component_inside_lot_through_parent, LotQ)


class Sorting(query.Sort):
    id = query.SortField(Device.id)
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
        if args['format']:
            ...
            return self.spreadsheet(query)
        else:
            devices = query.paginate(page=args['page'], per_page=30)  # type: Pagination
            ret = {
                'items': self.schema.dump(devices.items, many=True, nested=1),
                # todo pagination should be in Header like github
                # https://developer.github.com/v3/guides/traversing-with-pagination/
                'pagination': {
                    'page': devices.page,
                    'perPage': devices.per_page,
                    'total': devices.total,
                    'previous': devices.prev_num,
                    'next': devices.next_num
                },
                'url': request.path
            }
            return jsonify(ret)

    def spreadsheet(self, query):
        devices = []
        for device in query:
            d = DeviceRow(device)
            devices.append(d)

        titles = [name for name in devices[0].keys()] +
        rest = [[value for value in row.values()] for row in devices]


class DeviceRow(OrderedDict):
    NUMS = {
        Processor.t: 1
    }

    def __init__(self, device: Device) -> None:
        super().__init__()
        self.device = device
        self['Type'] = device.t
        if isinstance(device, Computer):
            self['Chassis'] = device.chassis
        self['Tag 1'] = self['Tag 2'] = self['Tag 3'] = ''
        for i, tag in zip(range(1, 3), device.tags):
            self['Tag {}'.format(i)] = format(tag)
        self['Serial Number'] = device.serial_number
        self['Price'] = device.price
        self['Model'] = device.model
        self['Manu...'] = device.manufacturer
        self['Regsitered in '] = device.created
        if isinstance(device, Computer):
            self['Processor'] = device.processor_model
            self['RAM (GB)'] = device.ram_size
            self['Size (MB)'] = device.data_storage_size
        rate = device.rate # type: Rate
        if rate:
            self['Rate'] = rate.rating
            self['Range'] = rate.rating_range
            self['Processor Rate'] = rate.processor_rate
            self['RAM Rate'] = rate.ram_rate
            self['Data Storage Rate'] = rate.data_storage_rate
        # New Update fields (necessaris?)
        # Origin note = Id-Donació
        # Target note = Id-Receptor
        # Partner = cadena de custodia (cadena de noms dels agents(entitas) implicats) [int]
        # Margin = percentatges de com es repeteix els guanys del preu de venta del dispositiu. [int]
        # Id invoice = id de la factura
        if isinstance(device, Computer):
            self.components()


    def components(self):
        assert isinstance(self.device, Computer)
        for type in app.resources[Component.t].subresources_types: # type: str
            max = self.NUMS.get(type, 4)
            i = 1
            for component in (r for r in self.device.components if r.type == type):
                self.fill_component(type, i, component)
                i += 1
                if i >= max:
                    break
            while i < max:
                self.fill_component(type, i)
                i += 1


    def fill_component(self, type, i, component = None):
        self['{} {} Serial Number'.format(type, i)] = component.serial_number if component else ''
        if isinstance(component, DataStorage):
            self['{} {} Compliance'.format()] = component.compliance


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
