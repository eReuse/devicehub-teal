"""Open Connect OIDC

Revision ID: abba37ff5c80
Revises:
Create Date: 2022-09-30 10:01:19.761864

"""
import citext
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'abba37ff5c80'
down_revision = None
branch_labels = None
depends_on = None


def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    op.create_table(
        'member_federated',
        sa.Column('dlt_id_provider', sa.BigInteger(), nullable=False),
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
        sa.Column('domain', citext.CIText(), nullable=False),
        sa.Column('client_id', citext.CIText(), nullable=True),
        sa.Column('client_secret', citext.CIText(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('dlt_id_provider'),
        sa.ForeignKeyConstraint(['user_id'], ['common.user.id'], ondelete='CASCADE'),
        schema=f'{get_inv()}',
    )

    op.create_table(
        'oauth2_client',
        sa.Column('id', sa.BigInteger(), nullable=False),
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
        sa.Column('client_id_issued_at', sa.BigInteger(), nullable=False),
        sa.Column('client_secret_expires_at', sa.BigInteger(), nullable=False),
        sa.Column('client_id', citext.CIText(), nullable=False),
        sa.Column('client_secret', citext.CIText(), nullable=False),
        sa.Column('client_metadata', citext.CIText(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('member_id', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['common.user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['member_id'],
            [f'{get_inv()}.member_federated.dlt_id_provider'],
            ondelete='CASCADE',
        ),
        schema=f'{get_inv()}',
    )

    op.create_table(
        'oauth2_code',
        sa.Column('id', sa.BigInteger(), nullable=False),
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
        sa.Column('client_id', citext.CIText(), nullable=True),
        sa.Column('code', citext.CIText(), nullable=False),
        sa.Column('redirect_uri', citext.CIText(), nullable=True),
        sa.Column('response_type', citext.CIText(), nullable=True),
        sa.Column('scope', citext.CIText(), nullable=True),
        sa.Column('nonce', citext.CIText(), nullable=True),
        sa.Column('code_challenge', citext.CIText(), nullable=True),
        sa.Column('code_challenge_method', citext.CIText(), nullable=True),
        sa.Column('auth_time', sa.BigInteger(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('member_id', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['common.user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['member_id'],
            [f'{get_inv()}.member_federated.dlt_id_provider'],
            ondelete='CASCADE',
        ),
        sa.UniqueConstraint('code'),
        schema=f'{get_inv()}',
    )

    op.create_table(
        'oauth2_token',
        sa.Column('id', sa.BigInteger(), nullable=False),
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
        sa.Column('client_id', citext.CIText(), nullable=True),
        sa.Column('token_type', citext.CIText(), nullable=True),
        sa.Column('access_token', citext.CIText(), nullable=False),
        sa.Column('refresh_token', citext.CIText(), nullable=True),
        sa.Column('scope', citext.CIText(), nullable=True),
        sa.Column('issued_at', sa.BigInteger(), nullable=False),
        sa.Column('access_token_revoked_at', sa.BigInteger(), nullable=False),
        sa.Column('refresh_token_revoked_at', sa.BigInteger(), nullable=False),
        sa.Column('expires_in', sa.BigInteger(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('member_id', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['common.user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['member_id'],
            [f'{get_inv()}.member_federated.dlt_id_provider'],
            ondelete='CASCADE',
        ),
        sa.UniqueConstraint('access_token'),
        schema=f'{get_inv()}',
    )

    op.execute(f"CREATE SEQUENCE {get_inv()}.oauth2_client_seq;")
    op.execute(f"CREATE SEQUENCE {get_inv()}.member_federated_seq;")
    op.execute(f"CREATE SEQUENCE {get_inv()}.oauth2_code_seq;")
    op.execute(f"CREATE SEQUENCE {get_inv()}.oauth2_token_seq;")


def downgrade():
    op.drop_table('oauth2_client', schema=f'{get_inv()}')
    op.execute(f"DROP SEQUENCE {get_inv()}.oauth2_client_seq;")

    op.drop_table('oauth2_code', schema=f'{get_inv()}')
    op.execute(f"DROP SEQUENCE {get_inv()}.oauth2_code_seq;")

    op.drop_table('oauth2_token', schema=f'{get_inv()}')
    op.execute(f"DROP SEQUENCE {get_inv()}.oauth2_token_seq;")

    op.drop_table('member_federated', schema=f'{get_inv()}')
    op.execute(f"DROP SEQUENCE {get_inv()}.member_federated_seq;")
