"""drop unique org for tag

Revision ID: 6a2a939d5668
Revises: eca457d8b2a4
Create Date: 2021-02-25 18:47:47.441195

"""
from alembic import op
from alembic import context


# revision identifiers, used by Alembic.
revision = '6a2a939d5668'
down_revision = 'eca457d8b2a4'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.drop_constraint('one tag id per organization', 'tag', schema=f'{get_inv()}')
    op.drop_constraint('one secondary tag per organization', 'tag', schema=f'{get_inv()}')
    op.create_primary_key('one tag id per owner',  'tag', ['id', 'owner_id'], schema=f'{get_inv()}'),
    op.create_unique_constraint('one secondary tag per owner',  'tag', ['secondary', 'owner_id'], schema=f'{get_inv()}'),


def downgrade():
    op.drop_constraint('one tag id per owner', 'tag', schema=f'{get_inv()}')
    op.drop_constraint('one secondary tag per owner', 'tag', schema=f'{get_inv()}')
    op.create_primary_key('one tag id per organization',  'tag', ['id', 'org_id'], schema=f'{get_inv()}'),
    op.create_unique_constraint('one secondary tag per organization',  'tag', ['secondary', 'org_id'], schema=f'{get_inv()}'),
