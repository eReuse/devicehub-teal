"""transfer

Revision ID: 054a3aea9f08
Revises: 8571fb32c912
Create Date: 2022-05-27 11:07:18.245322

"""
import citext
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '054a3aea9f08'
down_revision = '8571fb32c912'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    # creating transfer table
    op.create_table(
        'transfer',
        sa.Column(
            'updated',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'created',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', citext.CIText(), nullable=False),
        sa.Column('closed', sa.Boolean(), nullable=False),
        sa.Column(
            'description',
            citext.CIText(),
            nullable=False,
            comment='A comment about the action.',
        ),
        sa.Column('date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('lot_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['lot_id'], [f'{get_inv()}.lot.id']),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )

    # creating index
    op.create_index(
        op.f('ix_transfer_created'),
        'transfer',
        ['created'],
        unique=False,
        schema=f'{get_inv()}',
    )
    op.create_index(
        op.f('ix_transfer_updated'),
        'transfer',
        ['updated'],
        unique=False,
        schema=f'{get_inv()}',
    )
    op.create_index(
        'ix_transfer_id',
        'transfer',
        ['id'],
        unique=False,
        postgresql_using='hash',
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_index(
        op.f('ix_transfer_created'), table_name='transfer', schema=f'{get_inv()}'
    )
    op.drop_index(
        op.f('ix_transfer_updated'), table_name='transfer', schema=f'{get_inv()}'
    )
    op.drop_index(op.f('ix_transfer_id'), table_name='transfer', schema=f'{get_inv()}')
    op.drop_table('transfer', schema=f'{get_inv()}')
