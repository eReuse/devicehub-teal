"""add wbid user in snapshotErrors

Revision ID: 97bef94f7982
Revises: 23d9e7ebbd7d
Create Date: 2022-04-12 09:27:59.670911

"""
import citext
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '97bef94f7982'
down_revision = '23d9e7ebbd7d'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.add_column(
        'snapshot_errors',
        sa.Column('wbid', citext.CIText(), nullable=True),
        schema=f'{get_inv()}',
    )
    op.add_column(
        'snapshot_errors',
        sa.Column('owner_id', postgresql.UUID(), nullable=True),
        schema=f'{get_inv()}',
    )
    op.create_foreign_key(
        "fk_snapshot_errors_owner_id_user_id",
        "snapshot_errors",
        "user",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
        source_schema=f'{get_inv()}',
        referent_schema='common',
    )


def downgrade():
    op.drop_constraint(
        "fk_snapshot_errors_owner_id_user_id",
        "snapshot_errors",
        type_="foreignkey",
        schema=f'{get_inv()}',
    )
    op.drop_column('snapshot_errors', 'owner_id', schema=f'{get_inv()}')
