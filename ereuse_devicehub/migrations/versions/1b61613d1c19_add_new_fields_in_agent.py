"""add new fields in agent

Revision ID: 1b61613d1c19
Revises: 8571fb32c912
Create Date: 2022-04-06 12:23:37.644108

"""
import citext
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = '1b61613d1c19'
down_revision = '8571fb32c912'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.add_column(
        "agent",
        sa.Column("last_name", citext.CIText(), nullable=True),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_column('agent', 'last_name', schema=f'{get_inv()}')
