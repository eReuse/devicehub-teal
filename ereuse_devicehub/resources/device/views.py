import csv
import datetime
from io import StringIO

import marshmallow
from flask import current_app as app, render_template, request, make_response
from flask.json import jsonify
from flask_sqlalchemy import Pagination
from marshmallow import fields, fields as f, validate as v
from sqlalchemy.orm import aliased
from sqlalchemy.util import OrderedDict
from teal import query
from teal.cache import cache
from teal.resource import View

from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.query import SearchQueryParser, things_response
from ereuse_devicehub.resources import search
from ereuse_devicehub.resources.device.models import Component, Computer, Device, Manufacturer, \
    Display, Processor, GraphicCard, Motherboard, NetworkAdapter, DataStorage, RamModule, \
    SoundCard
from ereuse_devicehub.resources.device.search import DeviceSearch
from ereuse_devicehub.resources.event import models as events
from ereuse_devicehub.resources.lot.models import LotDeviceDescendants
from ereuse_devicehub.resources.tag.model import Tag


class OfType(f.Str):
    def __init__(self, column: db.Column, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.column = column

    def _deserialize(self, value, attr, data):
        v = super()._deserialize(value, attr, data)
        return self.column.in_(app.resources[v].subresources_types)


class RateQ(query.Query):
    rating = query.Between(events.Rate.rating, f.Float())
    appearance = query.Between(events.Rate.appearance, f.Float())
    functionality = query.Between(events.Rate.functionality, f.Float())


class TagQ(query.Query):
    id = query.Or(query.ILike(Tag.id), required=True)
    org = query.ILike(Tag.org)


class LotQ(query.Query):
    id = query.Or(query.Equal(LotDeviceDescendants.ancestor_lot_id, fields.UUID()))


class Filters(query.Query):
    id = query.Or(query.Equal(Device.id, fields.Integer()))
    type = query.Or(OfType(Device.type))
    model = query.ILike(Device.model)
    manufacturer = query.ILike(Device.manufacturer)
    serialNumber = query.ILike(Device.serial_number)
    # todo test query for rating (and possibly other filters)
    rating = query.Join((Device.id == events.EventWithOneDevice.device_id)
                        & (events.EventWithOneDevice.id == events.Rate.id),
                        RateQ)
    tag = query.Join(Device.id == Tag.device_id, TagQ)
    # todo This part of the query is really slow
    # And forces usage of distinct, as it returns many rows
    # due to having multiple paths to the same
    lot = query.Join(Device.id == LotDeviceDescendants.device_id, LotQ)


class Sorting(query.Sort):
    id = query.SortField(Device.id)
    created = query.SortField(Device.created)
    updated = query.SortField(Device.updated)


class DeviceView(View):
    QUERY_PARSER = SearchQueryParser()

    class FindArgs(marshmallow.Schema):
        search = f.Str()
        filter = f.Nested(Filters, missing=[])
        sort = f.Nested(Sorting, missing=[Device.id.asc()])
        page = f.Integer(validate=v.Range(min=1), missing=1)

    def get(self, id):
        """
        Devices view
        ---
        description: Gets a device or multiple devices.
        parameters:
          - name: id
            type: integer
            in: path}
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
    @cache(datetime.timedelta(minutes=1))
    def find(self, args: dict):
        """Gets many devices."""
        # Compute query
        query = self.query(args)
        devices = query.paginate(page=args['page'], per_page=30)  # type: Pagination
        return things_response(
            self.schema.dump(devices.items, many=True, nested=1),
            devices.page, devices.per_page, devices.total, devices.prev_num, devices.next_num
        )

    def query(self, args):
        query = Device.query.distinct()  # todo we should not force to do this if the query is ok
        search_p = args.get('search', None)
        if search_p:
            properties = DeviceSearch.properties
            tags = DeviceSearch.tags
            query = query.join(DeviceSearch).filter(
                search.Search.match(properties, search_p) | search.Search.match(tags, search_p)
            ).order_by(
                search.Search.rank(properties, search_p) + search.Search.rank(tags, search_p)
            )
        query = query.filter(*args['filter']).order_by(*args['sort'])
        if 'text/csv' in request.accept_mimetypes:
            return self.generate_post_csv(query)
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

    def generate_post_csv(self, query):
        """
        Get device query and put information in csv format
        :param query:
        :return:
        """
        data = StringIO()
        cw = csv.writer(data)
        first = True
        for device in query:
            d = DeviceRow(device)
            if first:
                cw.writerow(name for name in d.keys())
                first = False
            cw.writerow(v for v in d.values())
        output = make_response(data.getvalue())
        output.headers['Content-Disposition'] = 'attachment; filename=export.csv'
        output.headers['Content-type'] = 'text/csv'
        return output


class DeviceRow(OrderedDict):
    NUMS = {
        Display.t: 1,
        Processor.t: 2,
        GraphicCard.t: 2,
        Motherboard.t: 1,
        NetworkAdapter.t: 2,
        SoundCard.t: 2
    }

    def __init__(self, device: Device) -> None:
        super().__init__()
        self.device = device
        # General information about device
        self['Type'] = device.t
        if isinstance(device, Computer):
            self['Chassis'] = device.chassis
        self['Tag 1'] = self['Tag 2'] = self['Tag 3'] = ''
        for i, tag in zip(range(1, 3), device.tags):
            self['Tag {}'.format(i)] = format(tag)
        self['Serial Number'] = device.serial_number
        self['Model'] = device.model
        self['Manufacturer'] = device.manufacturer
        # self['State'] = device.last_event_of()
        self['Price'] = device.price
        self['Registered in'] = format(device.created, '%c')
        if isinstance(device, Computer):
            self['Processor'] = device.processor_model
            self['RAM (GB)'] = device.ram_size
            self['Storage Size (MB)'] = device.data_storage_size
        rate = device.rate
        if rate:
            self['Rate'] = rate.rating
            self['Range'] = rate.rating_range
            self['Processor Rate'] = rate.processor
            self['Processor Range'] = rate.workbench.processor_range
            self['RAM Rate'] = rate.ram
            self['RAM Range'] = rate.workbench.ram_range
            self['Data Storage Rate'] = rate.data_storage
            self['Data Storage Range'] = rate.workbench.data_storage_range
        # More specific information about components
        if isinstance(device, Computer):
            self.components()


    def components(self):
        """
        Function to get all components information of a device
        """
        assert isinstance(self.device, Computer)
        # todo put an input specific order (non alphabetic)
        for type in sorted(app.resources[Component.t].subresources_types):  # type: str
            max = self.NUMS.get(type, 4)
            if type not in ['Component', 'HardDrive', 'SolidStateDrive']:
                i = 1
                for component in (r for r in self.device.components if r.type == type):
                    self.fill_component(type, i, component)
                    i += 1
                    if i > max:
                        break
                while i <= max:
                    self.fill_component(type, i)
                    i += 1

    def fill_component(self, type, i, component=None):
        """
        Function to put specific information of components in OrderedDict (csv)
        :param type: type of component
        :param component: device.components
        """
        self['{} {}'.format(type, i)] = format(component) if component else ''
        self['{} {} Manufacturer'.format(type, i)] = component.serial_number if component else ''
        self['{} {} Model'.format(type, i)] = component.serial_number if component else ''
        self['{} {} Serial Number'.format(type, i)] = component.serial_number if component else ''

        """ Particular fields for component GraphicCard """
        if isinstance(component, GraphicCard):
            self['{} {} Memory (MB)'.format(type, i)] = component.memory

        """ Particular fields for component DataStorage.t -> (HardDrive, SolidStateDrive) """
        if isinstance(component, DataStorage):
            self['{} {} Size (MB)'.format(type, i)] = component.size
            self['{} {} Privacy'.format(type, i)] = component.privacy

        # todo decide if is relevant more info about Motherboard
        """ Particular fields for component Motherboard """
        if isinstance(component, Motherboard):
            self['{} {} Slots'.format(type, i)] = component.slots

        """ Particular fields for component Processor """
        if isinstance(component, Processor):
            self['{} {} Number of cores'.format(type, i)] = component.cores
            self['{} {} Speed (GHz)'.format(type, i)] = component.speed

        """ Particular fields for component RamModule """
        if isinstance(component, RamModule):
            self['{} {} Size (MB)'.format(type, i)] = component.size
            self['{} {} Speed (MHz)'.format(type, i)] = component.speed
            self['{} {} Size'.format(type, i)] = component.size

        # todo add Display size, ...
        # todo add NetworkAdapter speedLink?
        # todo add some ComputerAccessories


class ManufacturerView(View):
    class FindArgs(marshmallow.Schema):
        search = marshmallow.fields.Str(required=True,
                                        # Disallow like operators
                                        validate=lambda x: '%' not in x and '_' not in x)

    @cache(datetime.timedelta(days=1))
    def find(self, args: dict):
        search = args['search']
        manufacturers = Manufacturer.query \
            .filter(Manufacturer.name.ilike(search + '%')) \
            .paginate(page=1, per_page=6)  # type: Pagination
        return jsonify(
            items=app.resources[Manufacturer.t].schema.dump(
                manufacturers.items,
                many=True,
                nested=1
            )
        )
