"""backup dhid

Revision ID: 6b0880832b78
Revises: d7ea9a3b2da1
Create Date: 2022-09-07 12:53:25.827186

"""
import citext
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = '6b0880832b78'
down_revision = 'd7ea9a3b2da1'
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
        sa.Column('dhid_bk', citext.CIText(), unique=False, nullable=True),
        schema=f'{get_inv()}',
    )
    op.add_column(
        'device',
        sa.Column('phid_bk', citext.CIText(), unique=False, nullable=True),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_column('device', 'dhid_bk', schema=f'{get_inv()}')
    op.drop_column('device', 'phid_bk', schema=f'{get_inv()}')
