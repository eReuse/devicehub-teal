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
down_revision = '6a2a939d5668'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV

def upgrade():
    op.drop_table('trade', schema=f'{get_inv()}')
    op.create_table('offer',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('price', sa.Float(decimal_return_scale=4), nullable=True),
                    sa.Column('lot_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('date', sa.TIMESTAMP(timezone=True), nullable=True),
                    sa.Column('user_from_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('user_to_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('document_id', citext.CIText(), nullable=True),
                    sa.Column('currency',
                              sa.Enum('AFN', 'ARS', 'AWG', 'AUD', 'AZN', 'BSD', 'BBD', 'BDT', 'BYR', 'BZD', 'BMD',
                                      'BOB', 'BAM', 'BWP', 'BGN', 'BRL', 'BND', 'KHR', 'CAD', 'KYD', 'CLP', 'CNY',
                                      'COP', 'CRC', 'HRK', 'CUP', 'CZK', 'DKK', 'DOP', 'XCD', 'EGP', 'SVC', 'EEK',
                                      'EUR', 'FKP', 'FJD', 'GHC', 'GIP', 'GTQ', 'GGP', 'GYD', 'HNL', 'HKD', 'HUF',
                                      'ISK', 'INR', 'IDR', 'IRR', 'IMP', 'ILS', 'JMD', 'JPY', 'JEP', 'KZT', 'KPW',
                                      'KRW', 'KGS', 'LAK', 'LVL', 'LBP', 'LRD', 'LTL', 'MKD', 'MYR', 'MUR', 'MXN',
                                      'MNT', 'MZN', 'NAD', 'NPR', 'ANG', 'NZD', 'NIO', 'NGN', 'NOK', 'OMR', 'PKR',
                                      'PAB', 'PYG', 'PEN', 'PHP', 'PLN', 'QAR', 'RON', 'RUB', 'SHP', 'SAR', 'RSD',
                                      'SCR', 'SGD', 'SBD', 'SOS', 'ZAR', 'LKR', 'SEK', 'CHF', 'SRD', 'SYP', 'TWD',
                                      'THB', 'TTD', 'TRY', 'TRL', 'TVD', 'UAH', 'GBP', 'USD', 'UYU', 'UZS', 'VEF',
                                      'VND', 'YER', 'ZWD', name='currency'), nullable=False,
                              comment='The currency of this price as for ISO 4217.'),

                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.trade.id'], ),
                    sa.ForeignKeyConstraint(['user_from_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['user_to_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['lot_id'], [f'{get_inv()}.lot.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    op.create_table('trade',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('accepted_by_from', sa.Boolean(), nullable=False),
                    sa.Column('accepted_by_to', sa.Boolean(), nullable=False),
                    sa.Column('confirm_transfer', sa.Boolean(), nullable=False),
                    sa.Column('offer_id', postgresql.UUID(as_uuid=True), nullable=False),

                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.ForeignKeyConstraint(['offer_id'], [f'{get_inv()}.offer.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )


def downgrade():
    op.drop_table('offer', schema=f'{get_inv()}')
    op.drop_table('trade', schema=f'{get_inv()}')
    op.create_table('trade',
                    sa.Column('shipping_date', sa.TIMESTAMP(timezone=True), nullable=True,
                              comment='When are the devices going to be ready \n    \
                                      for shipping?\n    '),
                    sa.Column('invoice_number', citext.CIText(), nullable=True,
                              comment='The id of the invoice so they can be linked.'),
                    sa.Column('price_id', postgresql.UUID(as_uuid=True), nullable=True,
                              comment='The price set for this trade.            \n    \
                                      If no price is set it is supposed that the trade was\n   \
                                      not payed, usual in donations.\n        '),
                    sa.Column('to_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('confirms_id', postgresql.UUID(as_uuid=True), nullable=True,
                              comment='An organize action that this association confirms. \
                                      \n    \n    For example, a ``Sell`` or ``Rent``\n   \
                                      can confirm a ``Reserve`` action.\n    '),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['confirms_id'], [f'{get_inv()}.organize.id'], ),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.ForeignKeyConstraint(['price_id'], [f'{get_inv()}.price.id'], ),
                    sa.ForeignKeyConstraint(['to_id'], [f'{get_inv()}.agent.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )
