import datetime

import marshmallow
from flask import current_app as app, render_template, request
from flask.json import jsonify
from flask_sqlalchemy import Pagination
from teal.cache import cache
from teal.resource import View

from ereuse_devicehub import auth
from ereuse_devicehub.resources.device.models import Device, Manufacturer


class DeviceView(View):

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
        return self.schema.jsonify(Device.query, many=True)


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
