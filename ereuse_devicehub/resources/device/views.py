import datetime

import flask
import marshmallow
from ereuseapi.methods import API
from flask import Response
from flask import current_app as app
from flask import g, render_template, request, session
from flask.json import jsonify
from flask_sqlalchemy import Pagination
from marshmallow import fields
from marshmallow import fields as f
from marshmallow import validate as v
from sqlalchemy.util import OrderedSet

from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.query import SearchQueryParser, things_response
from ereuse_devicehub.resources import search
from ereuse_devicehub.resources.action import models as actions
from ereuse_devicehub.resources.action.models import Trade
from ereuse_devicehub.resources.device import states
from ereuse_devicehub.resources.device.models import Computer, Device, Manufacturer
from ereuse_devicehub.resources.device.search import DeviceSearch
from ereuse_devicehub.resources.lot.models import LotDeviceDescendants
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.teal import query
from ereuse_devicehub.teal.cache import cache
from ereuse_devicehub.teal.db import ResourceNotFound
from ereuse_devicehub.teal.marshmallow import ValidationError
from ereuse_devicehub.teal.resource import View


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
    devicehub_id = query.Or(query.ILike(Device.devicehub_id))
    type = query.Or(OfType(Device.type))
    model = query.ILike(Device.model)
    manufacturer = query.ILike(Device.manufacturer)
    serialNumber = query.ILike(Device.serial_number)
    # todo test query for rating (and possibly other filters)
    rating = query.Join(
        (Device.id == actions.ActionWithOneDevice.device_id)
        & (actions.ActionWithOneDevice.id == actions.Rate.id),
        RateQ,
    )
    tag = query.Join(Device.id == Tag.device_id, TagQ)
    # todo This part of the query is really slow
    # And forces usage of distinct, as it returns many rows
    # due to having multiple paths to the same
    lot = query.Join((Device.id == LotDeviceDescendants.device_id), LotQ)


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
        unassign = f.Integer(validate=v.Range(min=0, max=1), missing=0)

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
        dev = Device.query.filter_by(id=id, owner_id=g.user.id, active=True).one()
        if isinstance(dev, Computer):
            resource_def = app.resources['Computer']
            # TODO check how to handle the 'actions_one'
            patch_schema = resource_def.SCHEMA(
                only=['transfer_state', 'actions_one'], partial=True
            )
            json = request.get_json(schema=patch_schema)
            # TODO check how to handle the 'actions_one'
            json.pop('actions_one')
            if not dev:
                raise ValueError('Device non existent')
            for key, value in json.items():
                setattr(dev, key, value)
            db.session.commit()
            return Response(status=204)
        raise ValueError('Cannot patch a non computer')

    def one(self, id: str):
        """Gets one device."""
        if not request.authorization:
            return self.one_public(id)
        else:
            return self.one_private(id)

    def one_public(self, id: int):
        devices = Device.query.filter_by(devicehub_id=id, active=True).all()
        if not devices:
            devices = [Device.query.filter_by(dhid_bk=id, active=True).one()]
        device = devices[0]
        abstract = None
        if device.binding:
            return flask.redirect(device.public_link)

        if device.is_abstract() == 'Twin':
            abstract = device.placeholder.binding

        placeholder = device.binding or device.placeholder
        device_abstract = placeholder and placeholder.binding or device
        device_real = placeholder and placeholder.device or device
        return render_template(
            'devices/layout.html',
            placeholder=placeholder,
            device=device,
            device_abstract=device_abstract,
            device_real=device_real,
            states=states,
            abstract=abstract,
            user=g.user,
        )

    @auth.Auth.requires_auth
    def one_private(self, id: str):
        device = Device.query.filter_by(
            devicehub_id=id, owner_id=g.user.id, active=True
        ).first()
        if not device:
            return self.one_public(id)
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
            devices.page,
            devices.per_page,
            devices.total,
            devices.prev_num,
            devices.next_num,
        )

    def query(self, args):
        trades = Trade.query.filter(
            (Trade.user_from == g.user) | (Trade.user_to == g.user)
        ).distinct()

        trades_dev_ids = {d.id for t in trades for d in t.devices}

        query = (
            Device.query.filter(Device.active == True)
            .filter((Device.owner_id == g.user.id) | (Device.id.in_(trades_dev_ids)))
            .distinct()
        )

        unassign = args.get('unassign', None)
        search_p = args.get('search', None)
        if search_p:
            properties = DeviceSearch.properties
            tags = DeviceSearch.tags
            devicehub_ids = DeviceSearch.devicehub_ids
            query = (
                query.join(DeviceSearch)
                .filter(
                    search.Search.match(properties, search_p)
                    | search.Search.match(tags, search_p)
                    | search.Search.match(devicehub_ids, search_p)
                )
                .order_by(
                    search.Search.rank(properties, search_p)
                    + search.Search.rank(tags, search_p)
                    + search.Search.rank(devicehub_ids, search_p)
                )
            )
        if unassign:
            subquery = LotDeviceDescendants.query.with_entities(
                LotDeviceDescendants.device_id
            )
            query = query.filter(Device.id.notin_(subquery))
        return query.filter(*args['filter']).order_by(*args['sort'])


class DeviceMergeView(View):
    """View for merging two devices
    Ex. ``device/<dev1_id>/merge/<dev2_id>``.
    """

    def post(self, dev1_id: int, dev2_id: int):
        device = self.merge_devices(dev1_id, dev2_id)

        ret = self.schema.jsonify(device)
        ret.status_code = 201

        db.session.commit()
        return ret

    @auth.Auth.requires_auth
    def merge_devices(self, dev1_id: int, dev2_id: int) -> Device:
        """Merge the current device with `with_device` (dev2_id) by
        adding all `with_device` actions under the current device, (dev1_id).

        This operation is highly costly as it forces refreshing
        many models in session.
        """
        # base_device = Device.query.filter_by(id=dev1_id, owner_id=g.user.id).one()
        self.base_device = Device.query.filter_by(id=dev1_id, owner_id=g.user.id).one()
        self.with_device = Device.query.filter_by(id=dev2_id, owner_id=g.user.id).one()

        if self.base_device.allocated or self.with_device.allocated:
            # Validation than any device is allocated
            msg = 'The device is allocated, please deallocated before merge.'
            raise ValidationError(msg)

        if not self.base_device.type == self.with_device.type:
            # Validation than we are speaking of the same kind of devices
            raise ValidationError('The devices is not the same type.')

        # Adding actions of self.with_device
        with_actions_one = [
            a
            for a in self.with_device.actions
            if isinstance(a, actions.ActionWithOneDevice)
        ]
        with_actions_multiple = [
            a
            for a in self.with_device.actions
            if isinstance(a, actions.ActionWithMultipleDevices)
        ]

        # Moving the tags from `with_device` to `base_device`
        # Union of tags the device had plus the (potentially) new ones
        self.base_device.tags.update([x for x in self.with_device.tags])
        self.with_device.tags.clear()  # We don't want to add the transient dummy tags
        db.session.add(self.with_device)

        # Moving the actions from `with_device` to `base_device`
        for action in with_actions_one:
            if action.parent:
                action.parent = self.base_device
            else:
                self.base_device.actions_one.add(action)
        for action in with_actions_multiple:
            if action.parent:
                action.parent = self.base_device
            else:
                self.base_device.actions_multiple.add(action)

        # Keeping the components of with_device
        components = OrderedSet(c for c in self.with_device.components)
        self.base_device.components = components

        # Properties from with_device
        self.merge()

        db.session().add(self.base_device)
        db.session().final_flush()
        return self.base_device

    def merge(self):
        """Copies the physical properties of the base_device to the with_device.
        This method mutates base_device.
        """
        for field_name, value in self.with_device.physical_properties.items():
            if value is not None:
                setattr(self.base_device, field_name, value)

        self.base_device.hid = self.with_device.hid
        self.base_device.set_hid()


class ManufacturerView(View):
    class FindArgs(marshmallow.Schema):
        search = marshmallow.fields.Str(
            required=True,
            # Disallow like operators
            validate=lambda x: '%' not in x and '_' not in x,
        )

    @cache(datetime.timedelta(days=1))
    def find(self, args: dict):
        search = args['search']
        manufacturers = Manufacturer.query.filter(
            Manufacturer.name.ilike(search + '%')
        ).paginate(
            page=1, per_page=6
        )  # type: Pagination
        return jsonify(
            items=app.resources[Manufacturer.t].schema.dump(
                manufacturers.items, many=True, nested=1
            )
        )
