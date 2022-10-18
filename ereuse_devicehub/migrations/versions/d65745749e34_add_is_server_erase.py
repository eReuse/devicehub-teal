"""add is_server_erase

Revision ID: d65745749e34
Revises: a13ed6ad0e3e
Create Date: 2022-10-17 13:20:29.875274

"""
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = 'd65745749e34'
down_revision = 'a13ed6ad0e3e'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.add_column(
        'snapshot',
        sa.Column('is_server_erase', sa.Boolean(), nullable=True),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_column('snapshot', 'is_server_erase', schema=f'{get_inv()}')
