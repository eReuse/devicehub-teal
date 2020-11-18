import uuid
# from typing import Callable, Iterable, Tuple
from flask import g, request
# from flask.json import jsonify
from teal.resource import View

from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.query import things_response
from ereuse_devicehub.resources.action.models import Allocate, Deallocate


class AllocateView(View):
    @auth.Auth.requires_auth
    def get(self, id: uuid.UUID) -> Allocate:
        return super().get(id)

    @auth.Auth.requires_auth
    def post(self):
        """ Create one allocate """
        res_json = request.get_json()
        allocate = Allocate(**res_json)
        db.session.add(allocate)
        db.session().final_flush()
        ret = self.schema.jsonify(allocate)
        ret.status_code = 201
        db.session.commit()
        return ret

    def find(self, args: dict):
        allocates = Allocate.query.filter_by(author=g.user) \
            .order_by(Allocate.created.desc()) \
            .paginate(per_page=200)
        return things_response(
            self.schema.dump(allocates.items, many=True, nested=0),
            allocates.page, allocates.per_page, allocates.total,
            allocates.prev_num, allocates.next_num
        )

    def one(self, id: uuid.UUID):
        """Gets one action."""
        allocate = Allocate.query.filter_by(id=id, author=g.user).one()
        return self.schema.jsonify(allocate, nested=2)


class DeAllocateView(View):
    @auth.Auth.requires_auth
    def get(self, id: uuid.UUID) -> Allocate:
        return super().get(id)

    @auth.Auth.requires_auth
    def post(self):
        """ Create one Deallocate """
        res_json = request.get_json()
        deallocate = Deallocate(**res_json)
        db.session.add(deallocate)
        db.session().final_flush()
        ret = self.schema.jsonify(deallocate)
        ret.status_code = 201
        db.session.commit()
        return ret

    def find(self, args: dict):
        deallocates = Deallocate.query.filter_by(author=g.user) \
            .order_by(Deallocate.created.desc()) \
            .paginate(per_page=200)
        return things_response(
            self.schema.dump(deallocates.items, many=True, nested=0),
            deallocates.page, deallocates.per_page, deallocates.total,
            deallocates.prev_num, deallocates.next_num
        )

    def one(self, id: uuid.UUID):
        """Gets one action."""
        deallocate = Deallocate.query.filter_by(id=id, author=g.user).one()
        res = self.schema.jsonify(deallocate, nested=2)
        return res
