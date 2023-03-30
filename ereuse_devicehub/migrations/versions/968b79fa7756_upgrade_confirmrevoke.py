"""upgrade confirmrevoke

Revision ID: 968b79fa7756
Revises: d22d230d2850
Create Date: 2021-11-12 19:18:39.135386

"""
from alembic import op
from alembic import context
import sqlalchemy as sa
import sqlalchemy_utils
import citext
from ereuse_devicehub import teal


# revision identifiers, used by Alembic.
revision = '968b79fa7756'
down_revision = 'd22d230d2850'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    con = op.get_bind()

    confirmsRevokes_sql = f"select * from {get_inv()}.action as action join {get_inv()}.confirm as confirm on action.id=confirm.id where action.type='ConfirmRevoke'"
    revokes_sql = f"select confirm.id, confirm.action_id from {get_inv()}.action as action join {get_inv()}.confirm as confirm on action.id=confirm.id where action.type='Revoke'"
    confirmsRevokes = [a for a in con.execute(confirmsRevokes_sql)]
    revokes = {ac.id: ac.action_id for ac in con.execute(revokes_sql)}

    for ac in confirmsRevokes:
        ac_id = ac.id
        revoke_id = ac.action_id
        trade_id = revokes[revoke_id]
        sql_action = f"update {get_inv()}.action set type='Revoke' where id='{ac_id}'"
        sql_confirm = (
            f"update {get_inv()}.confirm set action_id='{trade_id}' where id='{ac_id}'"
        )
        con.execute(sql_action)
        con.execute(sql_confirm)


def downgrade():
    pass
