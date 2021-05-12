"""add code device search

Revision ID: 8d34480c82c4
Revises: 8cb91ad1cc40
Create Date: 2021-04-26 12:00:36.635784

"""
from alembic import op
from alembic import context
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# from ereuse_devicehub.resources.device.search import DeviceSearch


# revision identifiers, used by Alembic.
revision = '8d34480c82c4'
down_revision = '8cb91ad1cc40'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.add_column('device_search',
                  sa.Column('devicehub_ids',
                            postgresql.TSVECTOR(),
                            nullable=True),
                  schema=f'{get_inv()}')

    op.create_index('devicehub_ids gist',
                    'device_search',
                    ['devicehub_ids'],
                    unique=False,
                    postgresql_using='gist',
                    schema=f'{get_inv()}')

    # Next of the migration execute: dh inv search

def downgrade():
    op.drop_index('devicehub_ids gist',
                  table_name='device_search',
                  schema=f'{get_inv()}')
    op.drop_column('device_search', 'devicehub_ids', schema=f'{get_inv()}')
