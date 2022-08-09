"""add owner to placeholder

Revision ID: d7ea9a3b2da1
Revises: 2b90b41a556a
Create Date: 2022-07-27 14:40:15.513820

"""
import citext
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2b90b41a556a'
down_revision = '3e3a67f62972'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade_data():
    con = op.get_bind()
    sql = f"select {get_inv()}.placeholder.id, {get_inv()}.device.owner_id from {get_inv()}.placeholder"
    sql += f" join {get_inv()}.device on {get_inv()}.device.id={get_inv()}.placeholder.device_id;"

    for c in con.execute(sql):
        id_placeholder = c.id
        id_owner = c.owner_id
        sql_update = f"update {get_inv()}.placeholder set owner_id='{id_owner}', is_abstract=False where id={id_placeholder};"
        con.execute(sql_update)


def upgrade():
    op.add_column(
        'placeholder',
        sa.Column('is_abstract', sa.Boolean(), nullable=True),
        schema=f'{get_inv()}',
    )
    op.add_column(
        'placeholder',
        sa.Column('components', citext.CIText(), nullable=True),
        schema=f'{get_inv()}',
    )
    op.add_column(
        'placeholder',
        sa.Column('owner_id', postgresql.UUID(), nullable=True),
        schema=f'{get_inv()}',
    )
    op.create_foreign_key(
        "fk_placeholder_owner_id_user_id",
        "placeholder",
        "user",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
        source_schema=f'{get_inv()}',
        referent_schema='common',
    )

    upgrade_data()


def downgrade():
    op.drop_constraint(
        "fk_placeholder_owner_id_user_id",
        "placeholder",
        type_="foreignkey",
        schema=f'{get_inv()}',
    )
    op.drop_column('placeholder', 'owner_id', schema=f'{get_inv()}')
    op.drop_column('placeholder', 'is_abstract', schema=f'{get_inv()}')
    op.drop_column('placeholder', 'components', schema=f'{get_inv()}')
