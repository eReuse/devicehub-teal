"""Owner in tags

Revision ID: b9b0ee7d9dca
Revises: 151253ac5c55
Create Date: 2020-06-30 17:41:28.611314

"""
import sqlalchemy as sa
from alembic import context
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b9b0ee7d9dca'
down_revision = 'fbb7e2a0cde0'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.add_column('tag', sa.Column('owner_id', postgresql.UUID(), nullable=True), schema=f'{get_inv()}')
    op.create_foreign_key("fk_tag_owner_id_user_id",
                          "tag", "user",
                          ["owner_id"], ["id"],
                          ondelete="SET NULL",
                          source_schema=f'{get_inv()}', referent_schema='common')


def downgrade():
    op.drop_constraint("fk_tag_owner_id_user_id", "tag", type_="foreignkey", schema=f'{get_inv()}')
    op.drop_column('tag', 'owner_id', schema=f'{get_inv()}')
