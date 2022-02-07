"""adding author action_device

Revision ID: d22d230d2850
Revises: 1bb2b5e0fae7
Create Date: 2021-11-10 17:37:12.304853

"""
import sqlalchemy as sa
from alembic import context
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd22d230d2850'
down_revision = '1bb2b5e0fae7'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.add_column('action_device',
                  sa.Column('author_id',
                      postgresql.UUID(),
                      nullable=True),
                  schema=f'{get_inv()}')
    op.create_foreign_key("fk_action_device_author",
                          "action_device", "user",
                          ["author_id"], ["id"],
                          ondelete="SET NULL",
                          source_schema=f'{get_inv()}',
                          referent_schema='common')


def downgrade():
    op.drop_constraint("fk_action_device_author", "device", type_="foreignkey", schema=f'{get_inv()}')
    op.drop_column('action_device', 'author_id', schema=f'{get_inv()}')
