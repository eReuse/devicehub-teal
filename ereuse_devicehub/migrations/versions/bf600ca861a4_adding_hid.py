"""empty message

Revision ID: bf600ca861a4
Revises: 68a5c025ab8e
Create Date: 2020-12-15 15:58:41.545563

"""
from alembic import context
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
import citext
from ereuse_devicehub import teal


# revision identifiers, used by Alembic.
revision = 'bf600ca861a4'
down_revision = '68a5c025ab8e'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    con = op.get_bind()
    sql = f"""
    select d.id, d.hid, dd.serial_number from {get_inv()}.computer as c 
        join {get_inv()}.device as d on c.id=d.id 
        inner join {get_inv()}.component as cmp on cmp.parent_id=c.id 
        inner join {get_inv()}.network_adapter as net on net.id=cmp.id 
        join {get_inv()}.device as dd on net.id=dd.id;
    """
    computers = con.execute(sql)
    hids = {}
    macs = {}
    for c in computers:
        hids[c.id] = c.hid
        if not c.serial_number:
            continue
        try:
            macs[c.id].append(c.serial_number)
            macs[c.id].sort()
        except:
            macs[c.id] = [c.serial_number]

    for id_dev, hid in hids.items():
        if not (id_dev and hid):
            continue
        if not id_dev in macs:
            continue
        mac = macs[id_dev][0]
        new_hid = "{}-{}".format(hid, mac)

        sql = f"update {get_inv()}.device set hid='{new_hid}' where id={id_dev};"
        con.execute(sql)


def downgrade():
    pass
