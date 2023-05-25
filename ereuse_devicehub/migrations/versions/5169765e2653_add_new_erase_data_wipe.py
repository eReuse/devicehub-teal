"""add new erase_data_wipe

Revision ID: 5169765e2653
Revises: 2f2ef041483a
Create Date: 2023-05-23 10:34:46.312074

"""
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5169765e2653'
down_revision = '2f2ef041483a'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade_data():
    con = op.get_bind()

    sql = f"select * from {get_inv()}.data_wipe;"
    for d in con.execute(sql):
        document_id = d.document_id
        author_id = d.author_id
        name = d.name
        device_id = d.device_id
        description = d.description
        start_time = d.start_time
        end_time = d.end_time
        severity = d.severity

        sql = f"""insert into {get_inv()}.erase_data_wipe 
            (name, description, start_time, end_time, severity, device_id, 
            author_id, document_id)
            values
            ({name}, {description}, {start_time}, {end_time}, {severity}, 
            {device_id}, {author_id}, {document_id});
        """
        con.execute(sql)

    con.execute(sql)


def upgrade():
    op.create_table(
        'erase_data_wipe',
        sa.Column('document_id', sa.BigInteger(), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['document_id'],
            [f'{get_inv()}.document.id'],
        ),
        sa.ForeignKeyConstraint(
            ['id'],
            [f'{get_inv()}.erase_basic.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_table('erase_data_wipe', schema=f'{get_inv()}')
