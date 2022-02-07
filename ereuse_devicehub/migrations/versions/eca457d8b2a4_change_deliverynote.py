"""change deliverynote

Revision ID: eca457d8b2a4
Revises: 0cbd839b09ef
Create Date: 2021-02-03 22:12:41.033661

"""
import citext
import sqlalchemy as sa
from alembic import op
from alembic import context
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'eca457d8b2a4'
down_revision = '0cbd839b09ef'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.drop_column('deliverynote', 'ethereum_address', schema=f'{get_inv()}')
    op.alter_column('deliverynote', 'deposit', new_column_name='amount', schema=f'{get_inv()}')
    op.alter_column('computer', 'deposit', new_column_name='amount', schema=f'{get_inv()}')
    op.alter_column('lot', 'deposit', new_column_name='amount', schema=f'{get_inv()}')
    op.drop_column('lot', 'deliverynote_address', schema=f'{get_inv()}')
    op.drop_column('computer', 'deliverynote_address', schema=f'{get_inv()}')
    op.drop_column('computer', 'ethereum_address', schema=f'{get_inv()}')
    op.drop_column('lot', 'receiver_address', schema=f'{get_inv()}')
    op.add_column('lot', sa.Column('receiver_address', citext.CIText(), 
                  sa.ForeignKey('common.user.email'), nullable=True),
                  schema=f'{get_inv()}')

    op.drop_column('user', 'ethereum_address', schema='common')


    op.drop_table('proof_function', schema=f'{get_inv()}')
    op.drop_table('proof_data_wipe', schema=f'{get_inv()}')
    op.drop_table('proof_transfer', schema=f'{get_inv()}')
    op.drop_table('proof_reuse', schema=f'{get_inv()}')
    op.drop_table('proof_recycling', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_proof_updated'), table_name='proof', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_proof_created'), table_name='proof', schema=f'{get_inv()}')
    op.drop_table('proof', schema=f'{get_inv()}')


def downgrade():
    op.add_column('deliverynote', sa.Column('ethereum_address', citext.CIText(), nullable=True), schema=f'{get_inv()}')
    op.alter_column('deliverynote', 'amount', new_column_name='deposit', schema=f'{get_inv()}')
    op.add_column('computer', sa.Column('deliverynote_address', citext.CIText(), nullable=True), schema=f'{get_inv()}')
    op.add_column('lot', sa.Column('deliverynote_address', citext.CIText(), nullable=True), schema=f'{get_inv()}')

    # =====
    op.alter_column('computer', 'amount', new_column_name='deposit', schema=f'{get_inv()}')
    op.alter_column('lot', 'amount', new_column_name='deposit', schema=f'{get_inv()}')

    # =====
    op.add_column('computer', sa.Column('ethereum_address', citext.CIText(), nullable=True), schema=f'{get_inv()}')
    op.add_column('user', sa.Column('ethereum_address', citext.CIText(), unique=True, nullable=True), schema='common')


    op.drop_column('lot', 'receiver_address', schema=f'{get_inv()}')
    op.add_column('lot', sa.Column('receiver_address', citext.CIText(), 
                  sa.ForeignKey('common.user.ethereum_address'), nullable=True),
                  schema=f'{get_inv()}')

    # =====
    op.create_table('proof',
                    sa.Column('updated', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'),
                              nullable=False,
                              comment='The last time Devicehub recorded a change for \n    this thing.\n    '),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'),
                              nullable=False, comment='When Devicehub created this.'),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('type', sa.Unicode(), nullable=False),
                    sa.Column('ethereum_hash', citext.CIText(), nullable=False),
                    sa.Column('device_id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['device_id'], [f'{get_inv()}.device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )
    op.create_index(op.f('ix_proof_created'), 'proof', ['created'], unique=False, schema=f'{get_inv()}')
    op.create_index(op.f('ix_proof_updated'), 'proof', ['updated'], unique=False, schema=f'{get_inv()}')
    op.create_table('proof_recycling',
                    sa.Column('collection_point', citext.CIText(), nullable=False),
                    sa.Column('date', sa.DateTime(), nullable=False),
                    sa.Column('contact', citext.CIText(), nullable=False),
                    sa.Column('ticket', citext.CIText(), nullable=False),
                    sa.Column('gps_location', citext.CIText(), nullable=False),
                    sa.Column('recycler_code', citext.CIText(), nullable=False),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.proof.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Proof reuse table
    op.create_table('proof_reuse',
                    sa.Column('receiver_segment', citext.CIText(), nullable=False),
                    sa.Column('id_receipt', citext.CIText(), nullable=False),
                    sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('receiver_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('price', sa.Integer(), nullable=True),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.proof.id'], ),
                    sa.ForeignKeyConstraint(['receiver_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['supplier_id'], ['common.user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Proof transfer table
    op.create_table('proof_transfer',
                    sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('receiver_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('deposit', sa.Integer(), nullable=True),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.proof.id'], ),
                    sa.ForeignKeyConstraint(['receiver_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['supplier_id'], ['common.user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )


    # ProofDataWipe table
    op.create_table('proof_data_wipe',
                    sa.Column('date', sa.DateTime(), nullable=False),
                    sa.Column('result', sa.Boolean(), nullable=False, comment='Identifies proof datawipe as a result.'),
                    sa.Column('proof_author_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('erasure_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['erasure_id'], [f'{get_inv()}.erase_basic.id'], ),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.proof.id'], ),
                    sa.ForeignKeyConstraint(['proof_author_id'], ['common.user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # PRoofFuntion
    op.create_table('proof_function',
                    sa.Column('disk_usage', sa.Integer(), nullable=True),
                    sa.Column('proof_author_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('rate_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.proof.id'], ),
                    sa.ForeignKeyConstraint(['proof_author_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['rate_id'], [f'{get_inv()}.rate.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )
