"""TestDataStorage_bigIntegers

Revision ID: 0103a9c96b2d
Revises: 3a3601ac8224
Create Date: 2021-07-21 08:56:48.342503

"""
from alembic import op, context
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0103a9c96b2d'
down_revision = '3a3601ac8224'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.alter_column('test_data_storage', 'reallocated_sector_count', type_=sa.BigInteger(), schema=f'{get_inv()}')
    op.alter_column('test_data_storage', 'power_cycle_count', type_=sa.Integer(), schema=f'{get_inv()}')
    op.alter_column('test_data_storage', 'reported_uncorrectable_errors', type_=sa.BigInteger(), schema=f'{get_inv()}')
    op.alter_column('test_data_storage', 'current_pending_sector_count', type_=sa.BigInteger(), schema=f'{get_inv()}')
    op.alter_column('test_data_storage', 'offline_uncorrectable', type_=sa.BigInteger(), schema=f'{get_inv()}')


def downgrade():
    op.alter_column('test_data_storage', 'reallocated_sector_count', type_=sa.SmallInteger(), schema=f'{get_inv()}')
    op.alter_column('test_data_storage', 'power_cycle_count', type_=sa.SmallInteger(), schema=f'{get_inv()}')
    op.alter_column('test_data_storage', 'reported_uncorrectable_errors', type_=sa.Integer(), schema=f'{get_inv()}')
    op.alter_column('test_data_storage', 'current_pending_sector_count', type_=sa.Integer(), schema=f'{get_inv()}')
    op.alter_column('test_data_storage', 'offline_uncorrectable', type_=sa.Integer(), schema=f'{get_inv()}')
