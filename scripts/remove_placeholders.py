from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.inventory.models import Transfer
from ereuse_devicehub.parser.models import PlaceholdersLog
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
from ereuse_devicehub.resources.device.models import Device, Placeholder
from ereuse_devicehub.resources.lot.models import LotDevice

app = Devicehub(inventory=DevicehubConfig.DB_SCHEMA)
app.app_context().push()


def main():
    manual_actions()
    change_lot()
    change_tags()
    remove_placeholders()


def remove_placeholders():
    devices = []
    for placeholder in Placeholder.query.all():
        device = placeholder.device
        binding = placeholder.binding
        if not device or not binding:
            continue
        devices.append(placeholder.device.id)

    for dev in Device.query.filter(Device.id.in_(devices)):
        db.session.delete(dev)

    for placeholder in Placeholder.query.all():
        device = placeholder.device
        binding = placeholder.binding
        if not device or not binding:
            continue
        for plog in PlaceholdersLog.query.filter_by(placeholder=placeholder).all():
            db.session.delete(plog)

        db.session.delete(placeholder)
    db.session.commit()


def change_lot():
    for placeholder in Placeholder.query.all():
        device = placeholder.device
        binding = placeholder.binding
        if not device or not binding:
            continue
        lots = [x for x in device.lots]
        for lot in lots:
            for rel_lot in LotDevice.query.filter_by(
                lot_id=lot.id, device_id=device.id
            ):
                if binding:
                    rel_lot.device_id = binding.id
    db.session.commit()


def change_tags():
    for placeholder in Placeholder.query.all():
        device = placeholder.device
        binding = placeholder.binding
        if not device or not binding:
            continue
        tags = [x for x in device.tags]
        for tag in tags:
            tag.device = binding
    db.session.commit()


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
        Transfer,
    )

    for action in MANUAL_ACTIONS:
        change_device(action)


def change_device(action):
    for ac in action.query.all():
        if hasattr(ac, 'device'):
            if not ac.device.placeholder:
                continue
            if not ac.device.placeholder.binding:
                continue
            ac.device = ac.device.placeholder.binding

        if hasattr(ac, 'devices'):
            for act in ActionDevice.query.filter_by(action_id=ac.id):
                if not act.device.placeholder:
                    continue
                if not act.device.placeholder.binding:
                    continue
                act.device = act.device.placeholder.binding
    db.session.commit()


if __name__ == '__main__':
    main()
    # db.session.commit()
