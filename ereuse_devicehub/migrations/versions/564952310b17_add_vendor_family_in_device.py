"""add vendor family in device

Revision ID: 564952310b17
Revises: af038a8a388c
Create Date: 2022-11-14 13:12:22.916848

"""
import citext
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = '564952310b17'
down_revision = 'af038a8a388c'
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
        sa.Column('family', citext.CIText(), nullable=True),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_column('device', 'family', schema=f'{get_inv()}')
