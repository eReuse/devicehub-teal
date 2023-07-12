"""add usody in enum software

Revision ID: be6847b24846
Revises: 5169765e2653
Create Date: 2023-07-11 14:07:08.887104

"""
from alembic import context, op

# revision identifiers, used by Alembic.
revision = 'be6847b24846'
down_revision = '5169765e2653'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.execute("ALTER TYPE snapshotsoftware ADD VALUE 'UsodyOS'")


def downgrade():
    # "select e.enumlabel FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = 'snapshotsoftware'"
    pass
