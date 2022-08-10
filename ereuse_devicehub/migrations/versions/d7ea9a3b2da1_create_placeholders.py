"""Create placeholders

Revision ID: 2b90b41a556a
Revises: 3e3a67f62972
Create Date: 2022-07-19 12:17:16.690865

"""
import copy

from alembic import context, op

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
from ereuse_devicehub.resources.device.models import Computer, Device, Placeholder
from ereuse_devicehub.resources.lot.models import LotDevice

# revision identifiers, used by Alembic.
revision = 'd7ea9a3b2da1'
down_revision = '2b90b41a556a'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def init_app():
    app = Devicehub(inventory=f'{get_inv()}')
    app.app_context().push()


def clone_computers():
    for computer in Computer.query.all():
        if computer.placeholder:
            continue
        clone_device(computer)


def clone_device(device):
    if device.binding:
        return

    if device.type == "Battery":
        device.size

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
    db.session.add(new_device)

    if hasattr(device, 'components'):
        for c in device.components:
            new_c = clone_device(c)
            new_c.parent = new_device

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
            if not ac.device.binding:
                continue
            ac.device = ac.device.binding.device

        if hasattr(ac, 'devices'):
            for act in ActionDevice.query.filter_by(action_id=ac.id):
                if not act.device.binding:
                    continue
                act.device = act.device.binding.device


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


def remove_manual_actions():
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
        remove_change_device(action)


def remove_change_device(action):
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


def remove_placeholders():
    devices = []
    for placeholder in Placeholder.query.all():
        device = placeholder.device
        binding = placeholder.binding
        if not binding:
            continue
        devices.append(placeholder.device.id)

    for dev in Device.query.filter(Device.id.in_(devices)):
        db.session.delete(dev)

    # for placeholder in Placeholder.query.all():
    #     device = placeholder.device
    #     binding = placeholder.binding
    #     if not device or not binding:
    #         continue
    #     for plog in PlaceholdersLog.query.filter_by(placeholder=placeholder).all():
    #         db.session.delete(plog)

    #     db.session.delete(placeholder)
    db.session.commit()


def upgrade():
    con = op.get_bind()
    devices = con.execute(f'select * from {get_inv()}.device')
    if not list(devices):
        return

    init_app()
    clone_computers()
    manual_actions()
    db.session.commit()


def downgrade():
    con = op.get_bind()
    devices = con.execute(f'select * from {get_inv()}.device')
    if not list(devices):
        return

    init_app()
    remove_manual_actions()
    change_lot()
    change_tags()
    remove_placeholders()
