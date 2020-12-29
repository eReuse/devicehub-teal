"""update_live

Revision ID: b4bd1538bad5
Revises: 3eb50297c365
Create Date: 2020-12-29 20:19:46.981207

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
import citext
import teal


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
    # Live action
    op.add_column('device',
        sa.Column('software_version', teal.db.StrictVersionType(length=32), nullable=False),
        sa.Column('licence_version', teal.db.StrictVersionType(length=32), nullable=False),
        sa.Column('software', sa.Enum('Workbench', 'WorkbenchAndroid', 'AndroidApp', 'Web', 
            'DesktopApp', 'WorkbenchDesktop',  name='snapshotsoftware'), nullable=False),
        nullable=True), schema=f'{get_inv()}')


def downgrade():
    op.drop_column('device',
        sa.Column('software_version', teal.db.StrictVersionType(length=32), nullable=False),
        sa.Column('licence_version', teal.db.StrictVersionType(length=32), nullable=False),
        sa.Column('software', sa.Enum('Workbench', 'WorkbenchAndroid', 'AndroidApp', 'Web', 
            'DesktopApp', 'WorkbenchDesktop',  name='snapshotsoftware'), nullable=False),
        nullable=True), schema=f'{get_inv()}')
