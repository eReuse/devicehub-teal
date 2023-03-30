"""documents

Revision ID: 7ecb8ff7abad
Revises: 3a3601ac8224
Create Date: 2021-07-19 14:46:42.375331

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
import citext
from ereuse_devicehub import teal

from alembic import op
from alembic import context
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '7ecb8ff7abad'
down_revision = '0103a9c96b2d'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    # Document table
    op.create_table(
        'document',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column(
            'updated',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
            comment='The last time Document recorded a change for \n    this thing.\n    ',
        ),
        sa.Column(
            'created',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
            comment='When Document created this.',
        ),
        sa.Column('document_type', sa.Unicode(), nullable=False),
        sa.Column('date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('id_document', sa.Unicode(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_name', sa.Unicode(), nullable=False),
        sa.Column('file_hash', sa.Unicode(), nullable=False),
        sa.Column('url', sa.Unicode(), nullable=True),
        sa.ForeignKeyConstraint(
            ['owner_id'],
            ['common.user.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )
    op.create_index(
        'generic_document_id',
        'document',
        ['id'],
        unique=False,
        postgresql_using='hash',
        schema=f'{get_inv()}',
    )
    op.create_index(
        op.f('ix_document_created'),
        'document',
        ['created'],
        unique=False,
        schema=f'{get_inv()}',
    )
    op.create_index(
        op.f('ix_document_updated'),
        'document',
        ['updated'],
        unique=False,
        schema=f'{get_inv()}',
    )
    op.create_index(
        'document_type_index',
        'document',
        ['document_type'],
        unique=False,
        postgresql_using='hash',
        schema=f'{get_inv()}',
    )

    # DataWipeDocument table
    op.create_table(
        'data_wipe_document',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('software', sa.Unicode(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ['id'],
            [f'{get_inv()}.document.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )

    # DataWipe table
    op.create_table(
        'data_wipe',
        sa.Column('document_id', sa.BigInteger(), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['document_id'],
            [f'{get_inv()}.document.id'],
        ),
        sa.ForeignKeyConstraint(
            ['id'],
            [f'{get_inv()}.action.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_table('data_wipe', schema=f'{get_inv()}')
    op.drop_table('data_wipe_document', schema=f'{get_inv()}')
    op.drop_table('document', schema=f'{get_inv()}')
