"""add rols to user

Revision ID: a8a86dbd5f51
Revises: 5169765e2653
Create Date: 2023-06-14 15:04:03.478157

"""
import citext
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = 'a8a86dbd5f51'
down_revision = '2f2ef041483a'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.add_column(
        'user',
        sa.Column('rols_dlt', type_=citext.CIText(), nullable=True),
        schema='common',
    )


def downgrade():
    op.drop_column('user', 'rols_dlt', schema='common')
