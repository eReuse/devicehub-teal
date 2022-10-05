"""id internal in placeholder

Revision ID: 626c17026ca7
Revises: e919fe0611ff
Create Date: 2022-10-03 19:25:00.581699

"""
import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = '626c17026ca7'
down_revision = 'e919fe0611ff'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade_datas():
    con = op.get_bind()
    sql = 'select id from common.user where phantom=false and active=true'
    users = con.execute(sql)
    for user in users:
        phid = 1
        user_id = user.id
        sql = f"""
            select id from {get_inv()}.placeholder where owner_id='{user_id}'
            order by id
        """
        placeholders = con.execute(sql)

        for p in placeholders:
            p_id = p.id
            sql = f"""
                update {get_inv()}.placeholder set phid='{phid}'
                where id='{p_id}'
            """
            con.execute(sql)
            phid += 1


def upgrade():
    op.add_column(
        'placeholder',
        sa.Column('id_device_internal', sa.Unicode(), nullable=True),
        schema=f'{get_inv()}',
    )

    upgrade_datas()


def downgrade():
    op.drop_column('placeholder', 'id_device_internal', schema=f'{get_inv()}')
