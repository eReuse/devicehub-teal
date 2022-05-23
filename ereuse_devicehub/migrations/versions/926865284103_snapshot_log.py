"""snapshot_log

Revision ID: 926865284103
Revises: 6f6771813f2e
Create Date: 2022-05-17 17:57:46.651106

"""
import citext
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '926865284103'
down_revision = '6f6771813f2e'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.create_table(
        'snapshots_log',
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
        sa.Column('description', citext.CIText(), nullable=True),
        sa.Column('version', citext.CIText(), nullable=True),
        sa.Column('sid', citext.CIText(), nullable=True),
        sa.Column('severity', sa.SmallInteger(), nullable=False),
        sa.Column('snapshot_uuid', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('snapshot_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['snapshot_id'],
            [f'{get_inv()}.snapshot.id'],
        ),
        sa.ForeignKeyConstraint(
            ['owner_id'],
            ['common.user.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )
    op.execute(f"CREATE SEQUENCE {get_inv()}.snapshots_log_seq START 1;")

    op.drop_table('snapshot_errors', schema=f'{get_inv()}')
    op.execute(f"DROP SEQUENCE {get_inv()}.snapshot_errors_seq;")


def downgrade():
    op.drop_table('snapshots_log', schema=f'{get_inv()}')
    op.execute(f"DROP SEQUENCE {get_inv()}.snapshots_log_seq;")

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
        sa.Column('sid', citext.CIText(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['owner_id'],
            ['common.user.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )
    op.execute(f"CREATE SEQUENCE {get_inv()}.snapshot_errors_seq START 1;")
