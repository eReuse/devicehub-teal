"""change deliverynote

Revision ID: eca457d8b2a4
Revises: 0cbd839b09ef
Create Date: 2021-02-03 22:12:41.033661

"""
from alembic import context
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
import citext
import teal


# revision identifiers, used by Alembic.
revision = 'eca457d8b2a4'
down_revision = '0cbd839b09ef'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.drop_column('deliverynote', 'ethereum_address', schema=f'{get_inv()}')
    op.drop_column('computer', 'deliverynote_address', schema=f'{get_inv()}')
    op.drop_column('lot', 'deliverynote_address', schema=f'{get_inv()}')


def downgrade():
    op.add_column('deliverynote', sa.Column('ethereum_address', citext.CIText(), nullable=True), schema=f'{get_inv()}')
    op.add_column('computer', sa.Column('deliverynote_address', citext.CIText(), nullable=True), schema=f'{get_inv()}')
    op.add_column('lot', sa.Column('deliverynote_address', citext.CIText(), nullable=True), schema=f'{get_inv()}')
