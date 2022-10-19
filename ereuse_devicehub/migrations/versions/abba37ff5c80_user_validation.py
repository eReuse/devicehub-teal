"""user validation

Revision ID: abba37ff5c80
Revises: d65745749e34
Create Date: 2022-09-30 10:01:19.761864

"""
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'abba37ff5c80'
down_revision = 'd65745749e34'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.create_table(
        'user_validation',
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
        sa.Column('joined_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('expired', sa.BigInteger(), nullable=False),
        sa.Column('token', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['common.user.id'],
        ),
        sa.UniqueConstraint('token'),
        schema=f'{get_inv()}',
    )

    op.execute(f"CREATE SEQUENCE {get_inv()}.user_validation_seq;")


def downgrade():
    op.drop_table('user_validation', schema=f'{get_inv()}')
    op.execute(f"DROP SEQUENCE {get_inv()}.user_validation_seq;")
