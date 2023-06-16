from authlib.integrations.sqla_oauth2 import (
    OAuth2AuthorizationCodeMixin,
    OAuth2ClientMixin,
    OAuth2TokenMixin,
)
from flask import g

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import User


class MemberFederated(Thing):
    __tablename__ = 'member_federated'

    dlt_id_provider = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(40), unique=False)
    # This client_id and client_secret is used for connected to this domain as
    # a client and this domain then is the server of auth
    client_id = db.Column(db.String(40), unique=False, nullable=True)
    client_secret = db.Column(db.String(60), unique=False, nullable=True)
    user_id = db.Column(
        db.UUID(as_uuid=True), db.ForeignKey(User.id, ondelete='CASCADE'), nullable=True
    )
    user = db.relationship(User)

    def __str__(self):
        return self.domain


class OAuth2Client(Thing, OAuth2ClientMixin):
    __tablename__ = 'oauth2_client'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey(User.id, ondelete='CASCADE'),
        nullable=False,
        default=lambda: g.user.id,
    )
    user = db.relationship(User)
    member_id = db.Column(
        db.Integer,
        db.ForeignKey('member_federated.dlt_id_provider', ondelete='CASCADE'),
    )
    member = db.relationship(MemberFederated)


class OAuth2AuthorizationCode(Thing, OAuth2AuthorizationCodeMixin):
    __tablename__ = 'oauth2_code'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.UUID(as_uuid=True), db.ForeignKey(User.id, ondelete='CASCADE')
    )
    user = db.relationship(User)
    member_id = db.Column(
        db.Integer,
        db.ForeignKey('member_federated.dlt_id_provider', ondelete='CASCADE'),
    )
    member = db.relationship('MemberFederated')


class OAuth2Token(Thing, OAuth2TokenMixin):
    __tablename__ = 'oauth2_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.UUID(as_uuid=True), db.ForeignKey(User.id, ondelete='CASCADE')
    )
    user = db.relationship(User)
    member_id = db.Column(
        db.Integer,
        db.ForeignKey('member_federated.dlt_id_provider', ondelete='CASCADE'),
    )
    member = db.relationship('MemberFederated')
