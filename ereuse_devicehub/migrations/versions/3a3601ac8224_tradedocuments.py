"""tradeDocuments

Revision ID: 3a3601ac8224
Revises: 51439cf24be8
Create Date: 2021-06-15 14:38:59.931818

"""
import citext
import sqlalchemy as sa
from ereuse_devicehub import teal
from alembic import op
from alembic import context
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '3a3601ac8224'
down_revision = '51439cf24be8'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.create_table(
        'trade_document',
        sa.Column(
            'updated',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
            comment='The last time Devicehub recorded a change for \n    this thing.\n    ',
        ),
        sa.Column(
            'created',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
            comment='When Devicehub created this.',
        ),
        sa.Column(
            'id',
            sa.BigInteger(),
            nullable=False,
            comment='The identifier of the device for this database. Used only\n    internally for software; users should not use this.\n    ',
        ),
        sa.Column(
            'date',
            sa.DateTime(),
            nullable=True,
            comment='The date of document, some documents need to have one date\n    ',
        ),
        sa.Column(
            'id_document',
            citext.CIText(),
            nullable=True,
            comment='The id of one document like invoice so they can be linked.',
        ),
        sa.Column(
            'description',
            citext.CIText(),
            nullable=True,
            comment='A description of document.',
        ),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'file_name',
            citext.CIText(),
            nullable=True,
            comment='This is the name of the file when user up the document.',
        ),
        sa.Column(
            'file_hash',
            citext.CIText(),
            nullable=True,
            comment='This is the hash of the file produced from frontend.',
        ),
        sa.Column(
            'url',
            citext.CIText(),
            teal.db.URL(),
            nullable=True,
            comment='This is the url where resides the document.',
        ),
        sa.ForeignKeyConstraint(
            ['lot_id'],
            [f'{get_inv()}.lot.id'],
        ),
        sa.ForeignKeyConstraint(
            ['owner_id'],
            ['common.user.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )
    # Action document table
    op.create_table(
        'action_trade_document',
        sa.Column('document_id', sa.BigInteger(), nullable=False),
        sa.Column('action_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['action_id'],
            [f'{get_inv()}.action.id'],
        ),
        sa.ForeignKeyConstraint(
            ['document_id'],
            [f'{get_inv()}.trade_document.id'],
        ),
        sa.PrimaryKeyConstraint('document_id', 'action_id'),
        schema=f'{get_inv()}',
    )

    op.create_index(
        'document_id',
        'trade_document',
        ['id'],
        unique=False,
        postgresql_using='hash',
        schema=f'{get_inv()}',
    )
    op.create_index(
        op.f('ix_trade_document_created'),
        'trade_document',
        ['created'],
        unique=False,
        schema=f'{get_inv()}',
    )
    op.create_index(
        op.f('ix_trade_document_updated'),
        'trade_document',
        ['updated'],
        unique=False,
        schema=f'{get_inv()}',
    )

    op.create_table(
        'confirm_document',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['id'],
            [f'{get_inv()}.action.id'],
        ),
        sa.ForeignKeyConstraint(
            ['action_id'],
            [f'{get_inv()}.action.id'],
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['common.user.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        schema=f'{get_inv()}',
    )


def downgrade():
    op.drop_table('action_trade_document', schema=f'{get_inv()}')
    op.drop_table('confirm_document', schema=f'{get_inv()}')
    op.drop_table('trade_document', schema=f'{get_inv()}')
