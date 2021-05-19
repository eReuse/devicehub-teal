import os
import time
from datetime import datetime
from flask import current_app as app, request, g, Response
from teal.resource import View

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.tradedocument.models import TradeDocument
from ereuse_devicehub.resources.hash_reports import insert_hash


def save_doc(data, user):
    """
    This function allow save a snapshot in json format un a TMP_SNAPSHOTS directory
    The file need to be saved with one name format with the stamptime and uuid joins
    """
    filename = data['file_name']
    lot = data['lot']
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour
    minutes = now.minute
    created = time.time()

    name_file = f"{year}-{month}-{day}-{hour}-{minutes}_{created}_{user}_{filename}"
    path_dir_base = os.path.join(app.config['PATH_DOCUMENTS_STORAGE'] , user)
    path = os.path.join(path_dir_base, str(lot.id))
    path_name = os.path.join(path, name_file)

    os.system(f'mkdir -p {path}')

    with open(path_name, 'wb') as doc_file:
        doc_file.write(data['file'])

    return path_name


class TradeDocumentView(View):

    def one(self, id: str):
        doc = TradeDocument.query.filter_by(id=id, owner=g.user).one()
        return self.schema.jsonify(doc)

    def post(self):
        """Add one document."""

        data = request.get_json(validate=True)
        data['path_name'] = save_doc(data, g.user.email)
        bfile = data.pop('file')
        insert_hash(bfile)

        doc = TradeDocument(**data)
        db.session.add(doc)
        db.session().final_flush()
        ret = self.schema.jsonify(doc)
        ret.status_code = 201
        db.session.commit()
        return ret

    def delete(self, id):
        doc = TradeDocument.query.filter_by(id=id, owner=g.user).one()
        db.session.delete(doc)
        db.session.commit()
        return Response(status=204)
