"""update_live

Revision ID: b4bd1538bad5
Revises: 3eb50297c365
Create Date: 2020-12-29 20:19:46.981207

"""
import sqlalchemy as sa
from ereuse_devicehub import teal
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b4bd1538bad5'
down_revision = '3eb50297c365'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    # op.execute("COMMIT")
    op.execute("ALTER TYPE snapshotsoftware ADD VALUE 'WorkbenchDesktop'")
    SOFTWARE = sa.dialects.postgresql.ENUM(
        'Workbench',
        'WorkbenchAndroid',
        'AndroidApp',
        'Web',
        'DesktopApp',
        'WorkbenchDesktop',
        name='snapshotsoftware',
        create_type=False,
        checkfirst=True,
    )

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
        sa.Column(
            'software_version', teal.db.StrictVersionType(length=32), nullable=False
        ),
        sa.Column(
            'licence_version', teal.db.StrictVersionType(length=32), nullable=False
        ),
        sa.Column('software', SOFTWARE, nullable=False),
        sa.ForeignKeyConstraint(
            ['id'],
            [f'{get_inv()}.action.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )


def downgrade():
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
    op.execute(
        "select e.enumlabel FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = 'snapshotsoftware'"
    )
