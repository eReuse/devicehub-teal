"""change command_timeout of TestDataStorage Action

Revision ID: 398826453b39
Revises: 8d34480c82c4
Create Date: 2021-05-12 12:41:02.808311

"""
from alembic import op, context
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '398826453b39'
down_revision = '8d34480c82c4'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.alter_column('test_data_storage', 'command_timeout', type_=sa.BigInteger(), schema=f'{get_inv()}')


def downgrade():
    op.alter_column('test_data_storage', 'command_timeout', type_=sa.Integer(), schema=f'{get_inv()}')
