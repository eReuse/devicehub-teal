import time

from flask import g, request, session
from flask_wtf import FlaskForm
from werkzeug.security import gen_salt
from wtforms import (
    BooleanField,
    SelectField,
    StringField,
    TextAreaField,
    URLField,
    validators,
)

from ereuse_devicehub.db import db
from ereuse_devicehub.modules.oidc.models import MemberFederated, OAuth2Client

AUTH_METHODS = [
    ('client_secret_basic', 'Client Secret Basic'),
    ('client_secret_post', 'Client Secret Post'),
    ('none', ''),
]


def split_by_crlf(s):
    return [v for v in s.splitlines() if v]


class CreateClientForm(FlaskForm):
    client_name = StringField(
        'Client Name', description="", render_kw={'class': "form-control"}
    )
    client_uri = URLField(
        'Client url', description="", render_kw={'class': "form-control"}
    )
    scope = StringField(
        'Allowed Scope', description="", render_kw={'class': "form-control"}
    )
    redirect_uris = TextAreaField(
        'Redirect URIs', description="", render_kw={'class': "form-control"}
    )
    grant_types = TextAreaField(
        'Allowed Grant Types', description="", render_kw={'class': "form-control"}
    )
    response_types = TextAreaField(
        'Allowed Response Types', description="", render_kw={'class': "form-control"}
    )
    token_endpoint_auth_method = SelectField(
        'Token Endpoint Auth Method',
        choices=AUTH_METHODS,
        description="",
        render_kw={'class': "form-control, form-select"},
    )

    def __init__(self, *args, **kwargs):
        user = g.user
        self.client = OAuth2Client.query.filter_by(user_id=user.id).first()
        if request.method == 'GET':
            if hasattr(self.client, 'client_metadata'):
                kwargs.update(self.client.client_metadata)
            grant_types = '\n'.join(kwargs.get('grant_types', ["authorization_code"]))
            redirect_uris = '\n'.join(kwargs.get('redirect_uris', []))
            response_types = '\n'.join(kwargs.get('response_types', ["code"]))
            kwargs['grant_types'] = grant_types
            kwargs['redirect_uris'] = redirect_uris
            kwargs['response_types'] = response_types

        super().__init__(*args, **kwargs)

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            return False

        domain = self.client_uri.data
        self.member = MemberFederated.query.filter_by(domain=domain).first()
        if not self.member:
            txt = ["This domain is not federated."]
            self.client_uri.errors = txt
            return False

        if self.member.user and self.member.user != g.user:
            txt = ["This domain is register from other user."]
            self.client_uri.errors = txt
            return False
        return True

    def save(self):
        if not self.client:
            client_id = gen_salt(24)
            self.client = OAuth2Client(client_id=client_id, user_id=g.user.id)
            self.client.client_id_issued_at = int(time.time())

        if self.token_endpoint_auth_method.data == 'none':
            self.client.client_secret = ''
        elif not self.client.client_secret:
            self.client.client_secret = gen_salt(48)

        self.member.client_id = self.client.client_id
        self.member.client_secret = self.client.client_secret
        if not self.member.user:
            self.member.user = g.user

        client_metadata = {
            "client_name": self.client_name.data,
            "client_uri": self.client_uri.data,
            "grant_types": split_by_crlf(self.grant_types.data),
            "redirect_uris": split_by_crlf(self.redirect_uris.data),
            "response_types": split_by_crlf(self.response_types.data),
            "scope": self.scope.data,
            "token_endpoint_auth_method": self.token_endpoint_auth_method.data,
        }
        self.client.set_client_metadata(client_metadata)
        self.client.member_id = self.member.dlt_id_provider

        if not self.client.id:
            db.session.add(self.client)

        db.session.commit()
        return self.client


class AuthorizeForm(FlaskForm):
    consent = BooleanField(
        'Consent?', [validators.Optional()], default=False, description=""
    )


class ListInventoryForm(FlaskForm):
    inventory = SelectField(
        'Select your inventory',
        choices=[],
        description="",
        render_kw={'class': "form-control, form-select"},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inventories = MemberFederated.query.filter(
            MemberFederated.client_id.isnot(None),
            MemberFederated.client_secret.isnot(None),
        )
        for i in self.inventories:
            self.inventory.choices.append((i.dlt_id_provider, i.domain))

    def save(self):
        next = request.args.get('next', '')
        iv = self.inventories.filter_by(dlt_id_provider=self.inventory.data).first()

        if not iv:
            return next

        session['next_url'] = next
        session['oidc'] = iv.dlt_id_provider
        client_id = iv.client_id
        dh = iv.domain + f'/oauth/authorize?client_id={client_id}'
        dh += '&scope=openid+profile+rols&response_type=code&nonce=abc'
        return dh
