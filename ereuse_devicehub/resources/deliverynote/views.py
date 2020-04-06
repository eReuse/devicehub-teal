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
from ereuse_devicehub.resources.device.models import Computer


class DeliverynoteView(View):

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

    def patch(self, id):
        patch_schema = self.resource_def.SCHEMA(only=('transfer_state',
                                                      'ethereum_address'), partial=True)
        d = request.get_json(schema=patch_schema)
        dlvnote = Deliverynote.query.filter_by(id=id).one()
        # device_fields = ['transfer_state',  'deliverynote_address']
        # computers = [x for x in dlvnote.transferred_devices if isinstance(x, Computer)]
        for key, value in d.items():
            setattr(dlvnote, key, value)
            # Transalate ethereum_address attribute
            # devKey = key
            # if key == 'ethereum_address':
            #     devKey = 'deliverynote_address'
            # if devKey in device_fields:
            #     for dev in computers:
            #         setattr(dev, devKey, value)
         
        db.session.commit()
        return Response(status=204)

    def one(self, id: uuid.UUID):
        """Get one delivery note"""
        deliverynote = Deliverynote.query.filter_by(id=id).one()  # type Deliverynote
        return self.schema.jsonify(deliverynote)
