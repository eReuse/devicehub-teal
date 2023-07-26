"""add solar panel

Revision ID: 8ccba3cb37c2
Revises: 5169765e2653
Create Date: 2023-07-26 09:23:21.326465

"""
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = '8ccba3cb37c2'
down_revision = '5169765e2653'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    # creating Solar panel device.

    op.create_table(
        'solar_panel',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ['id'],
            [f'{get_inv()}.device.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_table('solar_panel', schema=f'{get_inv()}')
