import datetime
import uuid

import marshmallow
from flask import current_app as app, render_template, request, Response
from flask.json import jsonify
from flask_sqlalchemy import Pagination
from marshmallow import fields, fields as f, validate as v, ValidationError, \
    Schema as MarshmallowSchema
from teal import query
from teal.cache import cache
from teal.resource import View

from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.query import SearchQueryParser, things_response
from ereuse_devicehub.resources import search
from ereuse_devicehub.resources.action import models as actions
from ereuse_devicehub.resources.device import states
from ereuse_devicehub.resources.device.models import Device, Manufacturer, Computer
from ereuse_devicehub.resources.device.search import DeviceSearch
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
    rating = query.Between(actions.Rate._rating, f.Float())
    appearance = query.Between(actions.Rate._appearance, f.Float())
    functionality = query.Between(actions.Rate._functionality, f.Float())


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
    rating = query.Join((Device.id == actions.ActionWithOneDevice.device_id)
                        & (actions.ActionWithOneDevice.id == actions.Rate.id),
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
        """Devices view
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

    def patch(self, id):
        dev = Device.query.filter_by(id=id).one()
        if isinstance(dev, Computer):
            resource_def = app.resources['Computer']
            # TODO check how to handle the 'actions_one'
            patch_schema = resource_def.SCHEMA(only=['ethereum_address', 'transfer_state', 'deliverynote_address', 'actions_one'], partial=True)
            json = request.get_json(schema=patch_schema)
            # TODO check how to handle the 'actions_one'
            json.pop('actions_one')
            if not dev:
                raise ValueError('Device non existent')
            for key, value in json.items():
                setattr(dev,key,value)
            db.session.commit()
            return Response(status=204)
        raise ValueError('Cannot patch a non computer')

    def one(self, id: int):
        """Gets one device."""
        if not request.authorization:
            return self.one_public(id)
        else:
            return self.one_private(id)

    def one_public(self, id: int):
        device = Device.query.filter_by(id=id).one()
        return render_template('devices/layout.html', device=device, states=states)

    @auth.Auth.requires_auth
    def one_private(self, id: int):
        device = Device.query.filter_by(id=id).one()
        return self.schema.jsonify(device)

    @auth.Auth.requires_auth
    # @cache(datetime.timedelta(minutes=1))
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
        return query.filter(*args['filter']).order_by(*args['sort'])


class DeviceMergeView(View):

    """View for merging two devices
    Ex. ``device/<id>/merge/id=X``.
    """
    class FindArgs(MarshmallowSchema):
        id = fields.Integer()

    def get_merge_id(self) -> uuid.UUID:
        args = self.QUERY_PARSER.parse(self.find_args, request, locations=('querystring',))
        return args['id']

    def post(self, id: uuid.UUID):
        device = Device.query.filter_by(id=id).one()
        with_device = self.get_merge_id()
        device.merge_device(with_device)

        db.session().final_flush()
        ret = self.schema.jsonify(device)
        ret.status_code = 201

        db.session.commit()
        return ret




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
