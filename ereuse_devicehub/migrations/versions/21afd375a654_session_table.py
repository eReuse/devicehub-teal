"""session_table

Revision ID: 21afd375a654
Revises: 6a2a939d5668
Create Date: 2021-04-13 11:18:27.720567

"""
from alembic import context
from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa
import sqlalchemy_utils
import citext
import teal

from ereuse_devicehub.resources.enums import SessionType


# revision identifiers, used by Alembic.
revision = '21afd375a654'
down_revision = '6a2a939d5668'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.create_table('session',
                    sa.Column('updated', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='The last time Devicehub recorded a change for \n    this thing.\n    '),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When Devicehub created this.'),
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.Column('expired', sa.BigInteger(), nullable=True),
                    sa.Column('token', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('type', teal.db.IntEnum(SessionType), nullable=False),
                    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.ForeignKeyConstraint(['user_id'], ['common.user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('token'),
                    schema='common'
    )
    op.create_index(op.f('ix_session_created'), 'session', ['created'], unique=False, schema='common')
    op.create_index(op.f('ix_session_updated'), 'session', ['updated'], unique=False, schema='common')


def downgrade():
    op.drop_table('trade', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_session_created'), table_name='session', schema='common')
    op.drop_index(op.f('ix_session_updated'), table_name='session', schema='common')
