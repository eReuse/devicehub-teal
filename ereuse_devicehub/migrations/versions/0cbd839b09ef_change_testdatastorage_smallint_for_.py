"""change TestDataStorage SmallInt for Integer

Revision ID: 0cbd839b09ef
Revises: b4bd1538bad5
Create Date: 2021-01-21 12:53:21.996221

"""
from alembic import context
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
import citext
from ereuse_devicehub import teal


# revision identifiers, used by Alembic.
revision = '0cbd839b09ef'
down_revision = 'b4bd1538bad5'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.alter_column(
        'test_data_storage',
        'current_pending_sector_count',
        type_=sa.Integer(),
        schema=f'{get_inv()}',
    )
    op.alter_column(
        'test_data_storage',
        'offline_uncorrectable',
        type_=sa.Integer(),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.alter_column(
        'test_data_storage',
        'current_pending_sector_count',
        type_=sa.SmallInteger(),
        schema=f'{get_inv()}',
    )
    op.alter_column(
        'test_data_storage',
        'offline_uncorrectable',
        type_=sa.SmallInteger(),
        schema=f'{get_inv()}',
    )
