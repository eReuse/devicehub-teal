import datetime
import uuid

from flask import Response, request

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.deliverynote.models import Deliverynote
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.teal.resource import View


class DeliverynoteView(View):
    def post(self):
        # Create delivery note
        dn = request.get_json()
        dlvnote = Deliverynote(**dn)
        # Create a lot
        lot_name = (
            dlvnote.document_id + "_" + datetime.datetime.utcnow().strftime("%Y-%m-%d")
        )
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
        patch_schema = self.resource_def.SCHEMA(only=('transfer_state'), partial=True)
        d = request.get_json(schema=patch_schema)
        dlvnote = Deliverynote.query.filter_by(id=id).one()
        # device_fields = ['transfer_state',  'deliverynote_address']
        # computers = [x for x in dlvnote.transferred_devices if isinstance(x, Computer)]
        for key, value in d.items():
            setattr(dlvnote, key, value)

        db.session.commit()
        return Response(status=204)

    def one(self, id: uuid.UUID):
        """Get one delivery note"""
        deliverynote = Deliverynote.query.filter_by(id=id).one()  # type Deliverynote
        return self.schema.jsonify(deliverynote)
