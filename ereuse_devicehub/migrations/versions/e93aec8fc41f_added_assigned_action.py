"""Added Assigned action

Revision ID: e93aec8fc41f
Revises: b9b0ee7d9dca
Create Date: 2020-11-17 13:22:56.790956

"""
from alembic import op
import sqlalchemy as sa
from alembic import context
import sqlalchemy_utils
import citext
from ereuse_devicehub import teal
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e93aec8fc41f'
down_revision = 'b9b0ee7d9dca'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    # Allocate action
    op.drop_table('allocate', schema=f'{get_inv()}')
    op.create_table(
        'allocate',
        sa.Column(
            'final_user_code',
            citext.CIText(),
            default='',
            nullable=True,
            comment="This is a internal code for mainteing the secrets of the personal datas of the new holder",
        ),
        sa.Column(
            'transaction',
            citext.CIText(),
            nullable=True,
            comment='The code used from the owner for relation with external tool.',
        ),
        sa.Column('end_users', sa.Numeric(precision=4), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['id'],
            [f'{get_inv()}.action.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )

    # Deallocate action
    op.drop_table('deallocate', schema=f'{get_inv()}')
    op.create_table(
        'deallocate',
        sa.Column(
            'transaction',
            citext.CIText(),
            nullable=True,
            comment='The code used from the owner for relation with external tool.',
        ),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['id'],
            [f'{get_inv()}.action.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )

    # Add allocate as a column in device
    op.add_column(
        'device',
        sa.Column('allocated', sa.Boolean(), nullable=True),
        schema=f'{get_inv()}',
    )

    # Receive action
    op.drop_table('receive', schema=f'{get_inv()}')

    # Live action
    op.drop_table('live', schema=f'{get_inv()}')
    op.create_table(
        'live',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'serial_number',
            sa.Unicode(),
            nullable=True,
            comment='The serial number of the Hard Disk in lower case.',
        ),
        sa.Column('usage_time_hdd', sa.Interval(), nullable=True),
        sa.Column('snapshot_uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['id'],
            [f'{get_inv()}.action.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_table('allocate', schema=f'{get_inv()}')
