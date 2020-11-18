import uuid
# from typing import Callable, Iterable, Tuple
from flask import g, request
# from flask.json import jsonify
from teal.resource import View

from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.query import things_response
from ereuse_devicehub.resources.action.models import Assigned


class AssignedView(View):
    @auth.Auth.requires_auth
    def get(self, id: uuid.UUID) -> Assigned:
        return super().get(id)
    
    @auth.Auth.requires_auth
    def post(self):
        """ Create one rent """
        res_json = request.get_json()
        assigned = Assigned(**res_json)
        db.session.add(assigned)
        db.session().final_flush()
        ret = self.schema.jsonify(assigned)
        ret.status_code = 201
        db.session.commit()
        return ret

    def find(self, args: dict):
        rents = Assigned.query.filter_by(author=g.user) \
            .order_by(Assigned.created.desc()) \
            .paginate(per_page=200)
        return things_response(
            self.schema.dump(rents.items, many=True, nested=0),
            rents.page, rents.per_page, rents.total, rents.prev_num, rents.next_num
        )

    def one(self, id: uuid.UUID):
        """Gets one action."""
        assigned = Assigned.query.filter_by(id=id, author=g.user).one()
        return self.schema.jsonify(assigned, nested=2)
