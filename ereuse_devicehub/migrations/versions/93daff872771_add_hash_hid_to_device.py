"""add hash hid to device

Revision ID: 93daff872771
Revises: 564952310b17
Create Date: 2022-12-13 10:14:45.500087

"""
import hashlib

import citext
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = '93daff872771'
down_revision = '564952310b17'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade_data():
    con = op.get_bind()
    sql = f"update {get_inv()}.computer set user_trusts='t';"
    con.execute(sql)

    dev_sql = f"select id, hid from {get_inv()}.device;"
    for d in con.execute(dev_sql):
        if not d.hid:
            continue
        dev_id = d.id
        chid = hashlib.sha3_256(d.hid.encode('utf-8')).hexdigest()
        sql = f"update {get_inv()}.device set chid='{chid}' where id={dev_id};"
        con.execute(sql)

    con.execute(sql)


def upgrade():
    op.add_column(
        'computer',
        sa.Column('user_trusts', sa.Boolean(), default=True, nullable=True),
        schema=f'{get_inv()}',
    )

    op.add_column(
        'device',
        sa.Column('chid', citext.CIText(), nullable=True),
        schema=f'{get_inv()}',
    )

    upgrade_data()

    op.alter_column('computer', 'user_trusts', nullable=False, schema=f'{get_inv()}')


def downgrade():
    op.drop_column('computer', 'user_trusts', schema=f'{get_inv()}')
    op.drop_column('device', 'chid', schema=f'{get_inv()}')
