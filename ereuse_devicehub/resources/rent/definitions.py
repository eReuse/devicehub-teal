from typing import Callable, Iterable, Tuple
from flask import g
from flask.json import jsonify
from ereuse_devicehub.resources import action as act
from ereuse_devicehub.resources.action.models import Rent
from ereuse_devicehub.resources.device.models import Device
from teal.resource import Converters, Resource, View
from ereuse_devicehub import auth
from ereuse_devicehub.query import things_response


class RentingView(View):
    @auth.Auth.requires_auth
    def get(self, id):
        return super().get(id)
    
    @auth.Auth.requires_auth
    def post(self):
        """ Create one rent """
        return jsonify('ok')

    def find(self, args: dict):
        rents = Rent.query.filter() \
            .order_by(Rent.created.desc()) \
            .paginate(per_page=200)
        return things_response(
            self.schema.dump(rents.items, many=True, nested=0),
            rents.page, rents.per_page, rents.total, rents.prev_num, rents.next_num
        )


class RentDef(Resource):
    VIEW = RentingView
    SCHEMA = act.schemas.Rent
