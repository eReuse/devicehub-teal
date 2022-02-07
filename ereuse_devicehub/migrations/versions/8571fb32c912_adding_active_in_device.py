"""adding active in device

Revision ID: 8571fb32c912
Revises: 968b79fa7756
Create Date: 2021-10-05 12:27:09.685227

"""
from alembic import op, context
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8571fb32c912'
down_revision = '968b79fa7756'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade_data():
    con = op.get_bind()
    sql = f"update {get_inv()}.device set active='t';"
    con.execute(sql)


def upgrade():
    op.add_column('device', sa.Column('active', sa.Boolean(),
                                      default=True,
                                      nullable=True),
                  schema=f'{get_inv()}')

    upgrade_data()
    op.alter_column('device', 'active', nullable=False, schema=f'{get_inv()}')


def downgrade():
    op.drop_column('device', 'active', schema=f'{get_inv()}')
