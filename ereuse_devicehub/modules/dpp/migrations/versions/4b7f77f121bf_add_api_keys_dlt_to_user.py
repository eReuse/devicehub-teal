"""add api_keys_dlt to user

Revision ID: 4b7f77f121bf
Revises:
Create Date: 2022-12-01 10:35:36.795035

"""
import citext
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = '4b7f77f121bf'
down_revision = None
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
        sa.Column('api_keys_dlt', type_=citext.CIText(), nullable=True),
        schema='common',
    )


def downgrade():
    op.drop_column('user', 'api_keys_dlt', schema='common')
