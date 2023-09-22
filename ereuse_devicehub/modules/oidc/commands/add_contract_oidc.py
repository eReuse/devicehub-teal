import json
import click
import logging
import time

from werkzeug.security import gen_salt

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.modules.oidc.models import MemberFederated, OAuth2Client


logger = logging.getLogger(__name__)


class AddContractOidc:
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        help = "Add client oidc"
        self.app.cli.command('add_contract_oidc', short_help=help)(self.run)

    @click.argument('email')
    @click.argument('client_name')
    @click.argument('client_uri')
    @click.argument('scope', required=False, default="openid profile rols")
    @click.argument('redirect_uris', required=False)
    @click.argument('grant_types', required=False, default=["authorization_code"])
    @click.argument('response_types', required=False, default=["code"])
    @click.argument('token_endpoint_auth_method', required=False, default="client_secret_basic")
    def run(
            self,
            email,
            client_name,
            client_uri,
            scope,
            redirect_uris,
            grant_types,
            response_types,
            token_endpoint_auth_method):

        self.email = email
        self.client_name = client_name
        self.client_uri = client_uri
        self.scope = scope
        self.redirect_uris = redirect_uris
        self.grant_types = grant_types
        self.response_types = response_types
        self.token_endpoint_auth_method = token_endpoint_auth_method

        if not self.redirect_uris:
            self.redirect_uris = ["{}/allow_code".format(client_uri)]

        self.member = MemberFederated.query.filter_by(domain=client_uri).first()
        self.user = User.query.filter_by(email=email).one()

        if not self.member:
            txt = "This domain is not federated."
            logger.error(txt)
            return

        if self.member.user and self.member.user != self.user:
            txt = "This domain is register from other user."
            logger.error(txt)
            return
        if self.member.client_id and self.member.client_secret:
            result = {
                "client_id": self.member.client_id,
                "client_secret": self.member.client_secret
            }
            print(json.dumps(result))
            return result

        result = self.save()
        result = {
            "client_id": result[0],
            "client_secret": result[1]
        }
        print(json.dumps(result))
        return result


    def save(self):
        client_id = gen_salt(24)
        client = OAuth2Client(client_id=client_id, user_id=self.user.id)
        client.client_id_issued_at = int(time.time())

        if self.token_endpoint_auth_method == 'none':
            client.client_secret = ''
        else:
            client.client_secret = gen_salt(48)

        self.member.client_id = client.client_id
        self.member.client_secret = client.client_secret
        self.member.user = self.user

        client_metadata = {
            "client_name": self.client_name,
            "client_uri": self.client_uri,
            "grant_types": self.grant_types,
            "redirect_uris": self.redirect_uris,
            "response_types": self.response_types,
            "scope": self.scope,
            "token_endpoint_auth_method": self.token_endpoint_auth_method,
        }
        client.set_client_metadata(client_metadata)
        client.member_id = self.member.dlt_id_provider

        db.session.add(client)

        db.session.commit()
        return client.client_id, client.client_secret
