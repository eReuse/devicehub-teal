import json
import sys

from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.action.models import Snapshot


def open_snapshot():
    path = sys.argv[2]
    f = open(path)
    txt = f.read()
    return json.loads(txt)


def get_family(snapshot):
    debug = snapshot.get('debug', {})
    lshw = debug.get('lshw', {})
    return lshw.get('configuration', {}).get('family', '')


def get_device(uuid):
    snapshot = Snapshot.query.filter_by(uuid=uuid).first()
    if snapshot:
        return snapshot.device


def main():
    schema = sys.argv[1]
    app = Devicehub(inventory=schema)
    app.app_context().push()
    snapshot = open_snapshot()
    uuid = snapshot.get('uuid')
    if not uuid:
        return
    family = get_family(snapshot)
    device = get_device(uuid)
    if not device:
        return
    device.family = family
    device.set_hid()
    db.session.commit()


if __name__ == '__main__':
    main()
