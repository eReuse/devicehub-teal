"""adding state actions

Revision ID: a0978ac6cf4a
Revises: 7ecb8ff7abad
Create Date: 2021-09-24 12:03:01.661679

"""
from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a0978ac6cf4a'
down_revision = '3ac2bc1897ce'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.create_table('action_status',
        sa.Column('rol_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
        sa.ForeignKeyConstraint(['rol_user_id'], ['common.user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}'
    )


def downgrade():
    op.drop_table('action_status', schema=f'{get_inv()}')
