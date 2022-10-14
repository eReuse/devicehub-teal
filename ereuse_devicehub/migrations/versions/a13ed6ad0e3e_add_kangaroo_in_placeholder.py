"""add kangaroo in placeholder

Revision ID: a13ed6ad0e3e
Revises: 626c17026ca7
Create Date: 2022-10-13 11:56:15.303218

"""
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = 'a13ed6ad0e3e'
down_revision = '626c17026ca7'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.add_column(
        'placeholder',
        sa.Column('kangaroo', sa.Boolean(), nullable=True),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_column('placeholder', 'kangaroo', schema=f'{get_inv()}')
