"""add digital passport dpp

Revision ID: 8334535d56fa
Revises: 4b7f77f121bf
Create Date: 2023-01-19 12:01:54.102326

"""
import citext
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8334535d56fa'
down_revision = '4b7f77f121bf'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.create_table(
        'proof',
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
        sa.Column('type', sa.Unicode(), nullable=False),
        sa.Column('documentId', citext.CIText(), nullable=True),
        sa.Column('documentSignature', citext.CIText(), nullable=True),
        sa.Column('normalizeDoc', citext.CIText(), nullable=True),
        sa.Column('timestamp', sa.BigInteger(), nullable=False),
        sa.Column('device_id', sa.BigInteger(), nullable=False),
        sa.Column('action_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('issuer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['action_id'],
            [f'{get_inv()}.action.id'],
        ),
        sa.ForeignKeyConstraint(
            ['device_id'],
            [f'{get_inv()}.device.id'],
        ),
        sa.ForeignKeyConstraint(
            ['issuer_id'],
            ['common.user.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )
    # op.create_index(op.f('ix_proof_created'), 'proof', ['created'], unique=False, schema=f'{get_inv()}')
    # op.create_index(op.f('ix_proof_timestamp'), 'proof', ['timestamp'], unique=False, schema=f'{get_inv()}')
    op.add_column(
        'snapshot',
        sa.Column('phid_dpp', citext.CIText(), nullable=True),
        schema=f'{get_inv()}',
    )
    op.add_column(
        'snapshot',
        sa.Column('json_wb', citext.CIText(), nullable=True),
        schema=f'{get_inv()}',
    )
    op.add_column(
        'snapshot',
        sa.Column('json_hw', citext.CIText(), nullable=True),
        schema=f'{get_inv()}',
    )

    op.create_table(
        'dpp',
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
        sa.Column('documentId', citext.CIText(), nullable=True),
        sa.Column('documentSignature', citext.CIText(), nullable=True),
        sa.Column('timestamp', sa.BigInteger(), nullable=False),
        sa.Column('device_id', sa.BigInteger(), nullable=False),
        sa.Column('snapshot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('issuer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['snapshot_id'],
            [f'{get_inv()}.snapshot.id'],
        ),
        sa.ForeignKeyConstraint(
            ['device_id'],
            [f'{get_inv()}.device.id'],
        ),
        sa.ForeignKeyConstraint(
            ['issuer_id'],
            ['common.user.id'],
        ),
        sa.Column('key', citext.CIText(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )
    op.execute(f"CREATE SEQUENCE {get_inv()}.proof_seq START 1;")
    op.execute(f"CREATE SEQUENCE {get_inv()}.dpp_seq START 1;")


def downgrade():
    op.drop_table('dpp', schema=f'{get_inv()}')
    op.drop_table('proof', schema=f'{get_inv()}')
    op.execute(f"DROP SEQUENCE {get_inv()}.proof_seq;")
    op.execute(f"DROP SEQUENCE {get_inv()}.dpp_seq;")
    # op.drop_index(op.f('ix_proof_created'), table_name='proof', schema=f'{get_inv()}')
    # op.drop_index(op.f('ix_proof_timestamp'), table_name='proof', schema=f'{get_inv()}')
    op.drop_column('snapshot', 'phid_dpp', schema=f'{get_inv()}')
    op.drop_column('snapshot', 'json_wb', schema=f'{get_inv()}')
    op.drop_column('snapshot', 'json_hw', schema=f'{get_inv()}')
