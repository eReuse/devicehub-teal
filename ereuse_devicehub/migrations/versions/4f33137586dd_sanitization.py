"""sanitization

Revision ID: 4f33137586dd
Revises: 93daff872771
Create Date: 2023-02-13 18:01:00.092527

"""
import sqlalchemy as sa
import teal
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4f33137586dd'
down_revision = '93daff872771'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.create_table(
        'sanitization_entity',
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
        sa.Column('company_name', sa.String(), nullable=True),
        sa.Column('logo', teal.db.URL(), nullable=True),
        sa.Column('responsable_person', sa.String(), nullable=True),
        sa.Column('supervisor_person', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['common.user.id'],
        ),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_table('sanitization_entity', schema=f'{get_inv()}')
