"""empty message

Revision ID: 378b6b147b46
Revises: bf600ca861a4
Create Date: 2020-12-16 11:45:13.339624

"""
import citext
import sqlalchemy as sa
import sqlalchemy_utils
from alembic import context
from alembic import op
from ereuse_devicehub import teal


# revision identifiers, used by Alembic.
revision = '378b6b147b46'
down_revision = 'bf600ca861a4'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.alter_column('computer', 'chassis', nullable=True, schema=f'{get_inv()}')
    op.alter_column('display', 'size', nullable=True, schema=f'{get_inv()}')
    op.alter_column('display', 'resolution_width', nullable=True, schema=f'{get_inv()}')
    op.alter_column('display', 'resolution_height', nullable=True, schema=f'{get_inv()}')
    op.alter_column('monitor', 'size', nullable=True, schema=f'{get_inv()}')
    op.alter_column('monitor', 'resolution_width', nullable=True, schema=f'{get_inv()}')
    op.alter_column('monitor', 'resolution_height', nullable=True, schema=f'{get_inv()}')
    # pass


def downgrade():
    pass
