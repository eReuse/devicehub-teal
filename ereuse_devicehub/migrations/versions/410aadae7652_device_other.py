"""device other

Revision ID: 410aadae7652
Revises: d65745749e34
Create Date: 2022-11-29 12:00:40.272121

"""
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = '410aadae7652'
down_revision = 'd65745749e34'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.create_table(
        'other',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ['id'],
            [f'{get_inv()}.device.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_table('other', schema=f'{get_inv()}')
