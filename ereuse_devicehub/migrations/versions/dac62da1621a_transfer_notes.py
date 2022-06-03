"""transfer notes

Revision ID: dac62da1621a
Revises: 054a3aea9f08
Create Date: 2022-06-03 12:04:39.486276

"""
import citext
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'dac62da1621a'
down_revision = '054a3aea9f08'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    # creating delivery note table
    op.create_table(
        'delivery_note',
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
        sa.Column('date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('number', citext.CIText(), nullable=True),
        sa.Column('weight', sa.Integer(), nullable=True),
        sa.Column('units', sa.Integer(), nullable=True),
        sa.Column('transfer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['transfer_id'], [f'{get_inv()}.transfer.id']),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )

    # creating index
    op.create_index(
        op.f('ix_delivery_note_created'),
        'delivery_note',
        ['created'],
        unique=False,
        schema=f'{get_inv()}',
    )
    op.create_index(
        op.f('ix_delivery_note_updated'),
        'delivery_note',
        ['updated'],
        unique=False,
        schema=f'{get_inv()}',
    )
    op.create_index(
        'ix_delivery_note_id',
        'delivery_note',
        ['id'],
        unique=False,
        postgresql_using='hash',
        schema=f'{get_inv()}',
    )

    # creating receiver note table
    op.create_table(
        'receiver_note',
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
        sa.Column('date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('number', citext.CIText(), nullable=True),
        sa.Column('weight', sa.Integer(), nullable=True),
        sa.Column('units', sa.Integer(), nullable=True),
        sa.Column('transfer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['transfer_id'], [f'{get_inv()}.transfer.id']),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )

    # creating index
    op.create_index(
        op.f('ix_receiver_note_created'),
        'receiver_note',
        ['created'],
        unique=False,
        schema=f'{get_inv()}',
    )
    op.create_index(
        op.f('ix_receiver_note_updated'),
        'receiver_note',
        ['updated'],
        unique=False,
        schema=f'{get_inv()}',
    )
    op.create_index(
        'ix_receiver_note_id',
        'receiver_note',
        ['id'],
        unique=False,
        postgresql_using='hash',
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_index(
        op.f('ix_delivery_note_created'),
        table_name='delivery_note',
        schema=f'{get_inv()}',
    )
    op.drop_index(
        op.f('ix_delivery_note_updated'),
        table_name='delivery_note',
        schema=f'{get_inv()}',
    )
    op.drop_index(
        op.f('ix_delivery_note_id'), table_name='delivery_note', schema=f'{get_inv()}'
    )
    op.drop_table('delivery_note', schema=f'{get_inv()}')

    op.drop_index(
        op.f('ix_receiver_note_created'),
        table_name='receiver_note',
        schema=f'{get_inv()}',
    )
    op.drop_index(
        op.f('ix_receiver_note_updated'),
        table_name='receiver_note',
        schema=f'{get_inv()}',
    )
    op.drop_index(
        op.f('ix_receiver_note_id'), table_name='receiver_note', schema=f'{get_inv()}'
    )
    op.drop_table('receiver_note', schema=f'{get_inv()}')
