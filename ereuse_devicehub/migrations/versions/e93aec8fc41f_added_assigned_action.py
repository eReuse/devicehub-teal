"""Added Assigned action

Revision ID: e93aec8fc41f
Revises: b9b0ee7d9dca
Create Date: 2020-11-17 13:22:56.790956

"""
from alembic import op
import sqlalchemy as sa
from alembic import context
import sqlalchemy_utils
import citext
import teal
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e93aec8fc41f'
down_revision = 'b9b0ee7d9dca'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.drop_table('allocate')
    op.create_table('allocate',
        sa.Column('code', citext.CIText(), nullable=True, comment=' This is a internal code for mainteing the secrets of the personal datas of the new holder '),
        sa.Column('end_users', sa.Numeric(precision=4), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}'
    )

    op.drop_table('deallocate')
    op.create_table('deallocate',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}'
    )


def downgrade():
    op.drop_table('allocate')
