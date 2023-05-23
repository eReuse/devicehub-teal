"""share lot

Revision ID: 2f2ef041483a
Revises: ac476b60d952
Create Date: 2023-04-26 16:04:21.560888

"""
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2f2ef041483a'
down_revision = 'ac476b60d952'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.create_table(
        'share_lot',
        sa.Column(
            'created',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_to_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('lot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['user_to_id'], ['common.user.id']),
        sa.ForeignKeyConstraint(['lot_id'], [f'{get_inv()}.lot.id']),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_table('share_lot', schema=f'{get_inv()}')
