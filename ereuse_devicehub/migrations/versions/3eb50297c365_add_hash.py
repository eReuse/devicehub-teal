"""empty message

Revision ID: 3eb50297c365
Revises: 378b6b147b46
Create Date: 2020-12-18 16:26:15.453694

"""

import citext
import sqlalchemy as sa

from alembic import op
from alembic import context
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '3eb50297c365'
down_revision = '378b6b147b46'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    # Report Hash table
    op.create_table('report_hash',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'),
                              nullable=False, comment='When Devicehub created this.'),
                    sa.Column('hash3', citext.CIText(), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )


def downgrade():
    op.drop_table('report_hash', schema=f'{get_inv()}')
