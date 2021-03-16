"""change trade action

Revision ID: 51439cf24be8
Revises: eca457d8b2a4
Create Date: 2021-03-15 17:40:34.410408

"""
from alembic import op
from alembic import context
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa
import citext


# revision identifiers, used by Alembic.
revision = '51439cf24be8'
down_revision = 'eca457d8b2a4'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    user_from_id = db.Column(UUID(as_uuid=True),
                             db.ForeignKey(User.id),
                             nullable=False,
                             default=lambda: g.user.id)
    user_from = db.relationship(User, primaryjoin=user_from_id == User.id)
    user_from_comment = """The user that offers the device due this deal."""
    user_to_id = db.Column(UUID(as_uuid=True),
                           db.ForeignKey(User.id),
                           nullable=False,
                           default=lambda: g.user.id)
    user_to = db.relationship(User, primaryjoin=user_to_id == User.id)
    user_to_comment = """The user that gets the device due this deal."""
    price = Column(Float(decimal_return_scale=2), nullable=True)
    date = Column(db.TIMESTAMP(timezone=True))
    user_to_string = Column(CIText())
    user_from_string = Column(CIText())
++++

    op.create_table('trade',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('date', sa.TIMESTAMP(timezone=True), nullable=True),
                    sa.Column('user_from_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('user_to_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('user_from_string', citext.CIText(), nullable=True),
                    sa.Column('user_to_string', citext.CIText(), nullable=True),
                    sa.Column('price', sa.Float(decimal_return_scale=4), nullable=True),

                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.ForeignKeyConstraint(['from_id'], [f'common.user.id'], ),
                    sa.ForeignKeyConstraint(['to_id'], [f'common.user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )


def downgrade():
    pass
