import copy

from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.action.models import (
    ActionDevice,
    Allocate,
    DataWipe,
    Deallocate,
    Management,
    Prepare,
    Ready,
    Recycling,
    Refurbish,
    ToPrepare,
    ToRepair,
    Use,
)
from ereuse_devicehub.resources.device.models import Computer, Placeholder

app = Devicehub(inventory=DevicehubConfig.DB_SCHEMA)
app.app_context().push()


def main():
    clone_computers()
    manual_actions()


def clone_computers():
    for computer in Computer.query.all():
        clone_device(computer)


def clone_device(device):
    if device.binding:
        return

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
    db.session.add(new_device)

    if hasattr(device, 'components'):
        for c in device.components:
            new_c = clone_device(c)
            new_c.parent = new_device

    placeholder = Placeholder(device=new_device, binding=device)
    db.session.add(placeholder)

    tags = [x for x in device.tags]
    for tag in tags:
        tag.device = new_device

    lots = [x for x in device.lots]
    for lot in lots:
        set_devices = lot.devices - {device}
        set_devices.add(new_device)
        lot.devices.update(set_devices)
    return new_device


def manual_actions():
    MANUAL_ACTIONS = (
        Recycling,
        Use,
        Refurbish,
        Management,
        Allocate,
        Deallocate,
        ToPrepare,
        Prepare,
        DataWipe,
        ToRepair,
        Ready,
    )

    for action in MANUAL_ACTIONS:
        change_device(action)


def change_device(action):
    for ac in action.query.all():
        # import pdb; pdb.set_trace()
        if hasattr(ac, 'device'):
            if not ac.device.binding:
                continue
            ac.device = ac.device.binding.device

        if hasattr(ac, 'devices'):
            for act in ActionDevice.query.filter_by(action_id=ac.id):
                if not act.device.binding:
                    continue
                act.device = act.device.binding.device


if __name__ == '__main__':
    main()
    db.session.commit()
