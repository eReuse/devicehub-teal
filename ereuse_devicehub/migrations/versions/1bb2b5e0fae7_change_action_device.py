"""
change action_device

Revision ID: 1bb2b5e0fae7
Revises: a0978ac6cf4a
Create Date: 2021-11-04 10:32:49.116399

"""
import sqlalchemy as sa
from alembic import context
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '1bb2b5e0fae7'
down_revision = 'a0978ac6cf4a'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade_data():
    con = op.get_bind()

    values = f"action_id, {get_inv()}.action.created"
    table = f"{get_inv()}.action_device"
    joins = f"inner join {get_inv()}.action"
    on = f"on {get_inv()}.action_device.action_id = {get_inv()}.action.id"
    sql = f"select {values} from {table} {joins} {on}"

    actions_devs = con.execute(sql)
    for a in actions_devs:
        action_id = a.action_id
        created = a.created
        sql = f"update {get_inv()}.action_device set created='{created}' where action_id='{action_id}';"
        con.execute(sql)


def upgrade():
    op.add_column('action_device',
                  sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'),
                            nullable=False, comment='When Devicehub created this.'),
                  schema=f'{get_inv()}')

    op.add_column('action_status',
                  sa.Column('trade_id', postgresql.UUID(as_uuid=True), nullable=True),
                  schema=f'{get_inv()}')

    op.create_foreign_key("fk_action_status_trade",
                          "action_status", "trade",
                          ["trade_id"], ["id"],
                          ondelete="SET NULL",
                          source_schema=f'{get_inv()}',
                          referent_schema=f'{get_inv()}')

    upgrade_data()


def downgrade():
    op.drop_constraint("fk_action_status_trade", "action_status", type_="foreignkey", schema=f'{get_inv()}')
    op.drop_column('action_device', 'created', schema=f'{get_inv()}')
    op.drop_column('action_status', 'trade_id', schema=f'{get_inv()}')
