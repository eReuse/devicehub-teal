"""adding weight to tradedocuments

Revision ID: 3ac2bc1897ce
Revises: 3a3601ac8224
Create Date: 2021-08-03 16:28:38.719686

"""
from alembic import op
import sqlalchemy as sa
from alembic import context
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '3ac2bc1897ce'
down_revision = '7ecb8ff7abad'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.add_column("trade_document", sa.Column("weight", sa.Float(decimal_return_scale=2), nullable=True), schema=f'{get_inv()}') 

    # DataWipeDocument table
    op.create_table('move_on_document',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column("weight", sa.Float(decimal_return_scale=2), nullable=True),
                    sa.Column('container_from_id', sa.BigInteger(), nullable=False),
                    sa.Column('container_to_id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['container_from_id'], [f'{get_inv()}.trade_document.id'], ),
                    sa.ForeignKeyConstraint(['container_to_id'], [f'{get_inv()}.trade_document.id'], ),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )


def downgrade():
    op.drop_column('trade_document', 'weight', schema=f'{get_inv()}')
    op.drop_table('move_on_document', schema=f'{get_inv()}')
