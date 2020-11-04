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
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    # We need get the actual computers with owner_id
    # because when add a column in device this reset the values of the owner_id
    # in the computer tables
    con = op.get_bind()
    # computers = con.execute(f"select id, owner_id from {get_inv()}.computer")

    op.add_column('device', sa.Column('owner_id', postgresql.UUID(), 
        sa.ForeignKeyConstraint(['owner_id'], ['common.user.id'], ),
        nullable=True), schema=f'{get_inv()}')
    op.create_foreign_key("fk_device_owner_id_user_id",
                          "device", "user",
                          ["owner_id"], ["id"],
                          ondelete="SET NULL",
                          source_schema=f'{get_inv()}', referent_schema='common')
    sql = f"select {get_inv()}.component.id, {get_inv()}.computer.owner_id from \
            {get_inv()}.component \
            inner join {get_inv()}.computer on \
            {get_inv()}.component.parent_id={get_inv()}.computer.id"

    components = con.execute(sql)
    for id_component, id_owner in components:
        _sql = f"update {get_inv()}.component set owner_id={id_owner} where id={id_component}"
        con.execute(_sql)



def downgrade():
    op.drop_constraint("fk_device_owner_id_user_id", "device", type_="foreignkey", schema=f'{get_inv()}')
    op.drop_column('device', 'owner_id', schema=f'{get_inv()}')
