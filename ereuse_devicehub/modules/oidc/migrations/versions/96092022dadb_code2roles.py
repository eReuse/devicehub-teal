"""code2roles

Revision ID: 96092022dadb
Revises: abba37ff5c80
Create Date: 2023-12-12 18:45:45.324285

"""
import citext
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '96092022dadb'
down_revision = 'abba37ff5c80'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.create_table(
        'code_roles',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column(
            'updated',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'created',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('code', citext.CIText(), nullable=False),
        sa.Column('roles', citext.CIText(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )
    op.execute(f"CREATE SEQUENCE {get_inv()}.code_roles_seq;")


    op.create_table(
        'code_roles',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column(
            'updated',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'created',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('code', citext.CIText(), nullable=False),
        sa.Column('roles', citext.CIText(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.execute(f"CREATE SEQUENCE code_roles_seq;")


def downgrade():
    op.drop_table('code_roles', schema=f'{get_inv()}')
    op.execute(f"DROP SEQUENCE {get_inv()}.code_roles_seq;")
    op.drop_table('code_roles')
    op.execute(f"DROP SEQUENCE code_roles_seq;")
