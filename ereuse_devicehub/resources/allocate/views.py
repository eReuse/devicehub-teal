from flask import g, request
from teal.resource import View

from ereuse_devicehub.db import db
from ereuse_devicehub.query import things_response
from ereuse_devicehub.resources.action.models import Allocate, Deallocate


class AllocateMix():
    model = None

    def post(self):
        """ Create one res_obj """
        res_json = request.get_json()
        res_obj = self.model(**res_json)
        db.session.add(res_obj)
        db.session().final_flush()
        ret = self.schema.jsonify(res_obj)
        ret.status_code = 201
        db.session.commit()
        return ret

    def find(self, args: dict):
        res_objs = self.model.query.filter_by(author=g.user) \
            .order_by(self.model.created.desc()) \
            .paginate(per_page=200)
        return things_response(
            self.schema.dump(res_objs.items, many=True, nested=0),
            res_objs.page, res_objs.per_page, res_objs.total,
            res_objs.prev_num, res_objs.next_num
        )


class AllocateView(AllocateMix, View):
    model = Allocate


class DeallocateView(AllocateMix, View):
    model = Deallocate
