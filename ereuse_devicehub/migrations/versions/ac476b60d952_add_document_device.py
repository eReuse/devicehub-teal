"""add document device

Revision ID: ac476b60d952
Revises: 4f33137586dd
Create Date: 2023-03-31 10:46:02.463007

"""
import citext
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

from ereuse_devicehub import teal

# revision identifiers, used by Alembic.
revision = 'ac476b60d952'
down_revision = '4f33137586dd'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.create_table(
        'device_document',
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
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            'type',
            citext.CIText(),
            nullable=True,
        ),
        sa.Column(
            'date',
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            'id_document',
            citext.CIText(),
            nullable=True,
        ),
        sa.Column(
            'description',
            citext.CIText(),
            nullable=True,
        ),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', sa.BigInteger(), nullable=False),
        sa.Column(
            'file_name',
            citext.CIText(),
            nullable=True,
        ),
        sa.Column(
            'file_hash',
            citext.CIText(),
            nullable=True,
        ),
        sa.Column(
            'url',
            citext.CIText(),
            teal.db.URL(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ['device_id'],
            [f'{get_inv()}.device.id'],
        ),
        sa.ForeignKeyConstraint(
            ['owner_id'],
            ['common.user.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_table('device_document', schema=f'{get_inv()}')
