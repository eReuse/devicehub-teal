"""add snapshot errors

Revision ID: 23d9e7ebbd7d
Revises: 17288b2a7440
Create Date: 2022-04-04 19:27:48.675387

"""
import citext
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '23d9e7ebbd7d'
down_revision = '17288b2a7440'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.create_table(
        'snapshot_errors',
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
        sa.Column('description', citext.CIText(), nullable=False),
        sa.Column('snapshot_uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('severity', sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )
    op.execute(f"CREATE SEQUENCE {get_inv()}.snapshot_errors_seq START 1;")


def downgrade():
    op.drop_table('snapshot_errors', schema=f'{get_inv()}')
    op.execute(f"DROP SEQUENCE {get_inv()}.snapshot_errors_seq;")
