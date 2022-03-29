"""change firewire

Revision ID: 17288b2a7440
Revises: 8571fb32c912
Create Date: 2022-03-29 11:49:39.270791

"""
from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import citext


# revision identifiers, used by Alembic.
revision = '17288b2a7440'
down_revision = '8571fb32c912'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.alter_column('motherboard', 'firewire', citext.CIText(), schema=f'{get_inv()}')
    op.add_column('computer', sa.Column('uuid', postgresql.UUID(as_uuid=True),
                                      nullable=True),
                  schema=f'{get_inv()}')


def downgrade():
    op.alter_column('motherboard', 'firewire', sa.SmallInteger(), schema=f'{get_inv()}')
