"""add part number to device

Revision ID: bcfda54aaf2f
Revises: 6b0880832b78
Create Date: 2022-09-13 16:29:35.403897

"""
import citext
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = 'bcfda54aaf2f'
down_revision = '6b0880832b78'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.add_column(
        'device',
        sa.Column('part_number', citext.CIText(), nullable=True),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_column('device', 'part_number', schema=f'{get_inv()}')
