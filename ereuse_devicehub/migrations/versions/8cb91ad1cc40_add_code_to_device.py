"""add code to device

Revision ID: 8cb91ad1cc40
Revises: 6a2a939d5668
Create Date: 2021-03-03 10:39:19.331027

"""
import citext
import sqlalchemy as sa
from alembic import op
from alembic import context

from ereuse_devicehub.resources.utils import hashcode


# revision identifiers, used by Alembic.
revision = '8cb91ad1cc40'
down_revision = '6a2a939d5668'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade_data():
    con = op.get_bind()
    devices = con.execute(f"select id from {get_inv()}.device")
    for d in devices:
        id_dev = d.id
        code = hashcode.encode(d.id)
        sql = f"update {get_inv()}.device set devicehub_id='{code}' where id={id_dev};"
        con.execute(sql)


def upgrade():
    op.add_column('device', sa.Column('devicehub_id', citext.CIText(),
                                      unique=True,
                                      nullable=True), schema=f'{get_inv()}')

    upgrade_data()


def downgrade():
    op.drop_column('device', 'devicehub_id', schema=f'{get_inv()}')
