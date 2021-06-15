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
down_revision = '21afd375a654'
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade_data():
    con = op.get_bind()
    sql = "update common.user set active='t';"
    con.execute(sql)
    sql = "update common.user set phantom='f';"
    con.execute(sql)


def upgrade():
    ## Trade
    currency = sa.Enum('AFN', 'ARS', 'AWG', 'AUD', 'AZN', 'BSD', 'BBD', 'BDT', 'BYR', 'BZD', 'BMD',
                       'BOB', 'BAM', 'BWP', 'BGN', 'BRL', 'BND', 'KHR', 'CAD', 'KYD', 'CLP', 'CNY',
                       'COP', 'CRC', 'HRK', 'CUP', 'CZK', 'DKK', 'DOP', 'XCD', 'EGP', 'SVC', 'EEK',
                       'EUR', 'FKP', 'FJD', 'GHC', 'GIP', 'GTQ', 'GGP', 'GYD', 'HNL', 'HKD', 'HUF',
                       'ISK', 'INR', 'IDR', 'IRR', 'IMP', 'ILS', 'JMD', 'JPY', 'JEP', 'KZT', 'KPW',
                       'KRW', 'KGS', 'LAK', 'LVL', 'LBP', 'LRD', 'LTL', 'MKD', 'MYR', 'MUR', 'MXN',
                       'MNT', 'MZN', 'NAD', 'NPR', 'ANG', 'NZD', 'NIO', 'NGN', 'NOK', 'OMR', 'PKR',
                       'PAB', 'PYG', 'PEN', 'PHP', 'PLN', 'QAR', 'RON', 'RUB', 'SHP', 'SAR', 'RSD',
                       'SCR', 'SGD', 'SBD', 'SOS', 'ZAR', 'LKR', 'SEK', 'CHF', 'SRD', 'SYP', 'TWD',
                       'THB', 'TTD', 'TRY', 'TRL', 'TVD', 'UAH', 'GBP', 'USD', 'UYU', 'UZS', 'VEF', name='currency', create_type=False, checkfirst=True, schema=f'{get_inv()}')


    op.drop_table('trade', schema=f'{get_inv()}')
    op.create_table('trade',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('price', sa.Float(decimal_return_scale=4), nullable=True),
                    sa.Column('lot_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('date', sa.TIMESTAMP(timezone=True), nullable=True),
                    sa.Column('user_from_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('user_to_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('document_id', citext.CIText(), nullable=True),
                    sa.Column('confirm', sa.Boolean(), nullable=True),
                    sa.Column('code', citext.CIText(), default='', nullable=True,
                        comment = "This code is used for traceability"),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.ForeignKeyConstraint(['user_from_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['user_to_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['lot_id'], [f'{get_inv()}.lot.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    op.add_column("trade", sa.Column("currency", currency, nullable=False), schema=f'{get_inv()}')


    op.create_table('confirm',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('action_id', postgresql.UUID(as_uuid=True), nullable=False),

                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.ForeignKeyConstraint(['action_id'], [f'{get_inv()}.action.id'], ),
                    sa.ForeignKeyConstraint(['user_id'], ['common.user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    ## User
    op.add_column('user', sa.Column('active', sa.Boolean(), default=True, nullable=True),
                  schema='common')
    op.add_column('user', sa.Column('phantom', sa.Boolean(), default=False, nullable=True),
                  schema='common')

    upgrade_data()

    op.alter_column('user', 'active', nullable=False, schema='common')
    op.alter_column('user', 'phantom', nullable=False, schema='common')


    ## TradeDocument
    op.create_table('trade_document',
                    sa.Column(
                        'updated',
                        sa.TIMESTAMP(timezone=True),
                        server_default=sa.text('CURRENT_TIMESTAMP'),
                        nullable=False,
                        comment='The last time Devicehub recorded a change for \n    this thing.\n    '
                    ),
                    sa.Column(
                        'created',
                        sa.TIMESTAMP(timezone=True),
                        server_default=sa.text('CURRENT_TIMESTAMP'),
                        nullable=False,
                        comment='When Devicehub created this.'
                    ),
                    sa.Column(
                        'id',
                        sa.BigInteger(),
                        nullable=False,
                        comment='The identifier of the device for this database. Used only\n    internally for software; users should not use this.\n    '
                    ),
                    sa.Column(
                        'date',
                        sa.DateTime(),
                        nullable=True,
                        comment='The date of document, some documents need to have one date\n    '
                    ),
                    sa.Column(
                        'id_document',
                        citext.CIText(),
                        nullable=True,
                        comment='The id of one document like invoice so they can be linked.'
                    ),
                    sa.Column(
                        'description',
                        citext.CIText(),
                        nullable=True,
                        comment='A description of document.'
                    ),
                    sa.Column(
                        'owner_id',
                        postgresql.UUID(as_uuid=True),
                        nullable=False
                    ),
                    sa.Column(
                        'lot_id',
                        postgresql.UUID(as_uuid=True),
                        nullable=False
                    ),
                    sa.Column(
                        'file_name',
                        citext.CIText(),
                        nullable=True,
                        comment='This is the name of the file when user up the document.'
                    ),
                    sa.Column(
                        'file_hash',
                         citext.CIText(),
                         nullable=True,
                         comment='This is the hash of the file produced from frontend.'
                    ),
                    sa.Column(
                        'url',
                        citext.CIText(),
                        nullable=True,
                        comment='This is the url where resides the document.'
                    ),
                    sa.ForeignKeyConstraint(['lot_id'], ['lot.id'],),
                    sa.ForeignKeyConstraint(['owner_id'], ['common.user.id'],),
                    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('document_id', 'trade_document', ['id'], unique=False, postgresql_using='hash')
    op.create_index(op.f('ix_trade_document_created'), 'trade_document', ['created'], unique=False)
    op.create_index(op.f('ix_trade_document_updated'), 'trade_document', ['updated'], unique=False)


def downgrade():
    op.drop_table('confirm', schema=f'{get_inv()}')
    op.drop_table('trade', schema=f'{get_inv()}')
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
    op.drop_column('user', 'active', schema='common')
    op.drop_column('user', 'phantom', schema='common')
