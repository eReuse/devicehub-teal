"""placeholder-monitors

Revision ID: e919fe0611ff
Revises: bcfda54aaf2f
Create Date: 2022-09-27 10:55:00.859262

"""
from alembic import context, op

from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.models import (
    Cellphone,
    ComputerMonitor,
    Display,
    Mobile,
    Monitor,
    Placeholder,
    Smartphone,
    Tablet,
)

# revision identifiers, used by Alembic.
revision = 'e919fe0611ff'
down_revision = 'bcfda54aaf2f'
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


def clone_monitors():
    devices = [ComputerMonitor, Monitor, Display, Smartphone, Tablet, Cellphone, Mobile]
    for dev in devices:
        for d in dev.query.all():
            if d.placeholder or d.binding:
                continue
            clone_device(d)


def clone_device(device):
    if not device.owner_id:
        return
    placeholder = Placeholder(
        device=device, is_abstract=False, owner_id=device.owner_id
    )
    db.session.add(placeholder)


def remove_placeholders():
    devices = [ComputerMonitor, Monitor, Display, Smartphone, Tablet, Cellphone, Mobile]
    for dev in devices:
        for d in dev.query.all():
            if d.placeholder and d.binding:
                continue
            remove_device(d)


def remove_device(device):
    if not device.owner_id:
        return
    placeholder = device.placeholder
    db.session.delete(placeholder)


def upgrade():
    con = op.get_bind()
    devices = con.execute(f'select * from {get_inv()}.device')
    if not list(devices):
        return

    init_app()
    clone_monitors()
    db.session.commit()


def downgrade():
    con = op.get_bind()
    devices = con.execute(f'select * from {get_inv()}.device')
    if not list(devices):
        return

    # init_app()
    # remove_placeholders()
    # db.session.commit()
