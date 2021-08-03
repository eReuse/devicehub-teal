"""adding weight to tradedocuments

Revision ID: 3ac2bc1897ce
Revises: 3a3601ac8224
Create Date: 2021-08-03 16:28:38.719686

"""
from alembic import op
import sqlalchemy as sa
from alembic import context


# revision identifiers, used by Alembic.
revision = '3ac2bc1897ce'
down_revision = '0103a9c96b2d'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.add_column("trade_document", sa.Column("weight", sa.Float(decimal_return_scale=2), nullable=True), schema=f'{get_inv()}') 


def downgrade():
    op.drop_column('trade_document', 'weight', schema=f'{get_inv()}')
