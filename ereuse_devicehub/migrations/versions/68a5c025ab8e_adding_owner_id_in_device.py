"""adding owner_id in device

Revision ID: 68a5c025ab8e
Revises: b9b0ee7d9dca
Create Date: 2020-10-30 11:48:34.992498

"""
import sqlalchemy as sa
from alembic import context
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '68a5c025ab8e'
down_revision = 'b9b0ee7d9dca'
branch_labels = None
depends_on = None


def get_inv():
    # import pdb; pdb.set_trace()
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    INV = 'dbtest'
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.add_column('device', sa.Column('owner_id', postgresql.UUID(), nullable=True), schema=f'{get_inv()}')
    op.create_foreign_key("fk_device_owner_id_user_id",
                          "device", "user",
                          ["owner_id"], ["id"],
                          ondelete="SET NULL",
                          source_schema=f'{get_inv()}', referent_schema='common')


def downgrade():
    op.drop_constraint("fk_device_owner_id_user_id", "device", type_="foreignkey", schema=f'{get_inv()}')
    op.drop_column('device', 'owner_id', schema=f'{get_inv()}')
