"""placeholder log

Revision ID: 3e3a67f62972
Revises: aeca9fb50cc6
Create Date: 2022-07-06 18:23:54.267003

"""
import citext
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3e3a67f62972'
down_revision = 'aeca9fb50cc6'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.create_table(
        'placeholders_log',
        sa.Column(
            'updated',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
            comment='The last time Devicehub recorded a change for \n    this thing.\n    ',
        ),
        sa.Column(
            'created',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
            comment='When Devicehub created this.',
        ),
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('source', citext.CIText(), nullable=True),
        sa.Column('type', citext.CIText(), nullable=True),
        sa.Column('severity', sa.SmallInteger(), nullable=False),
        sa.Column('placeholder_id', sa.BigInteger(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['placeholder_id'],
            [f'{get_inv()}.placeholder.id'],
        ),
        sa.ForeignKeyConstraint(
            ['owner_id'],
            ['common.user.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )
    op.execute("CREATE SEQUENCE placeholders_log_seq START 1;")


def downgrade():
    op.drop_table('placeholders_log', schema=f'{get_inv()}')
    op.execute("DROP SEQUENCE placeholders_log_seq;")
