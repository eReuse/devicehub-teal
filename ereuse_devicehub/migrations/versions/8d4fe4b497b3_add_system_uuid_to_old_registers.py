"""add system uuid to old registers

Revision ID: 8d4fe4b497b3
Revises: 73348969a583
Create Date: 2022-06-15 15:52:39.205192

"""
import os
from uuid import UUID

from alembic import context, op

# revision identifiers, used by Alembic.
revision = '8d4fe4b497b3'
down_revision = '73348969a583'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def update_db(con, system_uuid, snapshot_uuid):
    sql_snapshot = f'select id from {get_inv()}.snapshot where uuid=\'{snapshot_uuid}\''
    sql_device_id = f'select device_id from {get_inv()}.action_with_one_device where id in ({sql_snapshot})'
    sql = f'select id, system_uuid from {get_inv()}.computer where id in ({sql_device_id})'

    for device_id, db_system_uuid in con.execute(sql):
        if db_system_uuid:
            return

        sql = f'update {get_inv()}.computer set system_uuid=\'{system_uuid}\' where id=\'{device_id}\''
        con.execute(sql)


def update_to_little_endian(uuid):
    uuid = UUID(uuid)
    return UUID(bytes_le=uuid.bytes)


def upgrade():
    uuids = []
    system_uuids_file = 'system_uuids.csv'
    if os.path.exists(system_uuids_file):
        with open(system_uuids_file) as f:
            for x in f.read().split('\n'):
                z = x.split(';')
                if len(z) != 2:
                    continue

                x, y = z
                uuids.append([x.strip(), y.strip()])

    con = op.get_bind()
    for u in uuids[1:]:
        if u[0] == '':
            continue
        u[0] = update_to_little_endian(u[0])
        update_db(con, u[0], u[1])


def downgrade():
    pass
