import sys
import uuid

from decouple import config

from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.lot.models import Lot, ShareLot
from ereuse_devicehub.resources.user.models import User


def main():
    schema = config('DB_SCHEMA')
    app = Devicehub(inventory=schema)
    app.app_context().push()
    email = sys.argv[1]
    lot_id = sys.argv[2]
    id = uuid.uuid4()
    user = User.query.filter_by(email=email).first()
    lot = Lot.query.filter_by(id=lot_id).first()

    share_lot = ShareLot(id=id, lot=lot, user_to=user)

    db.session.add(share_lot)
    db.session.commit()


if __name__ == '__main__':
    main()
