"""add settings_version to snapshots

Revision ID: af038a8a388c
Revises: 410aadae7652
Create Date: 2022-11-30 16:21:05.768024

"""
import citext
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = 'af038a8a388c'
down_revision = '410aadae7652'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.add_column(
        'snapshot',
        sa.Column('settings_version', citext.CIText(), nullable=True),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_column('snapshot', 'settings_version', schema=f'{get_inv()}')
