"""add code to device

Revision ID: 8cb91ad1cc40
Revises: eca457d8b2a4
Create Date: 2021-03-03 10:39:19.331027

"""
import citext
import sqlalchemy as sa
from alembic import op
from alembic import context


# revision identifiers, used by Alembic.
revision = '8cb91ad1cc40'
down_revision = 'eca457d8b2a4'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.add_column('device', sa.Column('code', citext.CIText(),
                                      unique=True,
                                      nullable=True), schema=f'{get_inv()}')


def downgrade():
    op.drop_column('device', 'code', schema=f'{get_inv()}')
