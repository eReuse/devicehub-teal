"""add placeholder

Revision ID: aeca9fb50cc6
Revises: 8d4fe4b497b3
Create Date: 2022-06-27 13:09:30.497678

"""
import citext
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = 'aeca9fb50cc6'
down_revision = '8d4fe4b497b3'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    # creating placeholder table

    op.create_table(
        'placeholder',
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
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('phid', sa.Unicode(), nullable=False),
        sa.Column('id_device_supplier', sa.Unicode(), nullable=True),
        sa.Column('pallet', sa.Unicode(), nullable=True),
        sa.Column('info', citext.CIText(), nullable=True),
        sa.Column('device_id', sa.BigInteger(), nullable=False),
        sa.Column('binding_id', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], [f'{get_inv()}.device.id']),
        sa.ForeignKeyConstraint(['binding_id'], [f'{get_inv()}.device.id']),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )
    op.execute("CREATE SEQUENCE placeholder_seq START 1;")


def downgrade():
    op.drop_table('placeholder', schema=f'{get_inv()}')
    op.execute("DROP SEQUENCE placeholder_seq;")
