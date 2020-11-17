# from typing import Callable, Iterable, Tuple
# from flask import g
# from flask.json import jsonify
from teal.resource import View

from ereuse_devicehub import auth
from ereuse_devicehub.query import things_response
from ereuse_devicehub.resources.action.models import Assigned

class RentingView(View):
    @auth.Auth.requires_auth
    def get(self, id):
        return super().get(id)
    
    @auth.Auth.requires_auth
    def post(self):
        """ Create one rent """
        return super().get(id)
        # return jsonify('ok')

    def find(self, args: dict):
        rents = Assigned.query.filter() \
            .order_by(Assigned.created.desc()) \
            .paginate(per_page=200)
        return things_response(
            self.schema.dump(rents.items, many=True, nested=0),
            rents.page, rents.per_page, rents.total, rents.prev_num, rents.next_num
        )


