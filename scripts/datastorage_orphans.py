import copy
import sys

from flask import g

from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.models import DataStorage, Placeholder
from ereuse_devicehub.resources.lot.models import LotDevice


def clone_device(device):
    if device.phid():
        return

    g.user = device.owner

    old_devicehub_id = device.devicehub_id

    dict_device = copy.copy(device.__dict__)
    dict_device.pop('_sa_instance_state')
    dict_device.pop('id', None)
    dict_device.pop('devicehub_id', None)
    dict_device.pop('actions_multiple', None)
    dict_device.pop('actions_one', None)
    dict_device.pop('components', None)
    dict_device.pop('tags', None)
    dict_device.pop('system_uuid', None)
    new_device = device.__class__(**dict_device)
    new_device.devicehub_id = old_devicehub_id
    device.devicehub_id = None
    new_device.owner = device.owner
    if device.parent and device.parent.binding:
        new_device.parent = device.parent.binding.device

    db.session.add(new_device)

    placeholder = Placeholder(
        device=new_device, binding=device, is_abstract=True, owner_id=device.owner_id
    )
    db.session.add(placeholder)

    tags = [x for x in device.tags]
    for tag in tags:
        tag.device = new_device

    lots = [x for x in device.lots]
    for lot in lots:
        for rel_lot in LotDevice.query.filter_by(lot_id=lot.id, device=device):
            rel_lot.device = new_device
    return new_device


def main():
    schema = sys.argv[1]
    app = Devicehub(inventory=schema)
    app.app_context().push()
    for device in DataStorage.query.all():
        if not device.phid():
            clone_device(device)

    db.session.commit()


if __name__ == '__main__':
    main()
