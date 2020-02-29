import datetime
import uuid
from collections import deque
from enum import Enum
from typing import Dict, List, Set, Union

import marshmallow as ma
import teal.cache
from flask import Response, jsonify, request
from marshmallow import Schema as MarshmallowSchema, fields as f
from teal.marshmallow import EnumField
from teal.resource import View
from sqlalchemy.orm import joinedload

from ereuse_devicehub.db import db
from ereuse_devicehub.query import things_response
from ereuse_devicehub.resources.deliverynote.models import Deliverynote
from ereuse_devicehub.resources.lot.models import Lot


class DeliverynoteView(View):
    class FindArgs(MarshmallowSchema):
        """Allowed arguments for the ``find``
        method (GET collection) endpoint
        """
        search = f.Str(missing=None)

    def post(self):
        # Create delivery note
        dn = request.get_json()
        dlvnote = Deliverynote(**dn)
        # Create a lot
        lot_name = dlvnote.supplier_email + "_" + datetime.datetime.utcnow().strftime("%B-%d-%Y")
        new_lot = Lot(name=lot_name)
        dlvnote.lot_id = new_lot.id
        db.session.add(new_lot)
        db.session.add(dlvnote)
        db.session().final_flush()
        ret = self.schema.jsonify(dlvnote)
        ret.status_code = 201
        db.session.commit()
        return ret

    # def patch(self, id):
    #     patch_schema = self.resource_def.SCHEMA(only=('name', 'description', 'transfer_state', 'receiver_address', 'deposit', 'deliverynote_address', 'devices', 'owner_address'), partial=True)
    #     d = request.get_json(schema=patch_schema)
    #     dlvnote = Deliverynote.query.filter_by(id=id).one()
    #     device_fields = ['transfer_state', 'receiver_address', 'deposit', 'deliverynote_address', 'owner_address']
    #     computers = [x for x in dlvnote.all_devices if isinstance(x, Computer)]
    #     for key, value in d.items():
    #         setattr(dlvnote, key, value)
    #         if key in device_fields:
    #             for dev in computers:
    #                 setattr(dev, key, value)
    #     db.session.commit()
    #     return Response(status=204)

    def one(self, id: uuid.UUID):
        """Gets one action."""
        deliverynote = Deliverynote.query.filter_by(id=id).one()  # type: Deliverynote
        return self.schema.jsonify(deliverynote)

    @teal.cache.cache(datetime.timedelta(minutes=5))
    def find(self, args: dict):
        """Gets deliverynotes.

        By passing the value `UiTree` in the parameter `format`
        of the query you get a recursive nested suited for ui-tree::

             [
                {title: 'lot1',
                nodes: [{title: 'child1', nodes:[]}]
            ]

        Note that in this format filters are ignored.

        Otherwise it just returns the standard flat view of lots that
        you can filter.
        """
        query = Deliverynote.query
        if args['search']:
            query = query.filter(Deliverynote.name.ilike(args['search'] + '%'))
        dlvnote = query.paginate(per_page=6 if args['search'] else 30)
        return things_response(
            self.schema.dump(dlvnote.items, many=True, nested=0),
            dlvnote.page, dlvnote.per_page, dlvnote.total, dlvnote.prev_num, dlvnote.next_num
        )

    def delete(self, id):
        dlvnote = Deliverynote.query.filter_by(id=id).one()
        dlvnote.delete()
        db.session.commit()
        return Response(status=204)
