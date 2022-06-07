"""change wbid for sid

Revision ID: 6f6771813f2e
Revises: 97bef94f7982
Create Date: 2022-04-25 10:52:11.767569

"""
import citext
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = '6f6771813f2e'
down_revision = '97bef94f7982'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade_datas():
    con = op.get_bind()
    sql = f"select * from {get_inv()}.snapshot;"
    snapshots = con.execute(sql)
    for snap in snapshots:
        wbid = snap.wbid
        if wbid:
            sql = f"""update {get_inv()}.snapshot set sid='{wbid}'
                where wbid='{wbid}';"""
            con.execute(sql)

    sql = f"select wbid from {get_inv()}.snapshot_errors;"
    snapshots = con.execute(sql)
    for snap in snapshots:
        wbid = snap.wbid
        if wbid:
            sql = f"""update {get_inv()}.snapshot set sid='{wbid}'
                where wbid='{wbid}';"""
            con.execute(sql)


def upgrade():
    op.add_column(
        'snapshot',
        sa.Column('sid', citext.CIText(), nullable=True),
        schema=f'{get_inv()}',
    )

    op.add_column(
        'snapshot_errors',
        sa.Column('sid', citext.CIText(), nullable=True),
        schema=f'{get_inv()}',
    )
    upgrade_datas()
    op.drop_column('snapshot', 'wbid', schema=f'{get_inv()}')
    op.drop_column('snapshot_errors', 'wbid', schema=f'{get_inv()}')


def downgrade():
    op.drop_column('snapshot', 'sid', schema=f'{get_inv()}')
    op.drop_column('snapshot_errors', 'sid', schema=f'{get_inv()}')
