"""system_uuid instead of uuid

Revision ID: 73348969a583
Revises: dac62da1621a
Create Date: 2022-06-15 12:27:23.170313

"""
from alembic import context, op

# revision identifiers, used by Alembic.
revision = '73348969a583'
down_revision = 'dac62da1621a'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.alter_column(
        'computer', 'uuid', new_column_name="system_uuid", schema=f'{get_inv()}'
    )


def downgrade():
    op.alter_column(
        'computer', 'system_uuid', new_column_name="uuid", schema=f'{get_inv()}'
    )
