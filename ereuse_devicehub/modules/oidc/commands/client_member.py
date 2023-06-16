import click

from ereuse_devicehub.db import db
from ereuse_devicehub.modules.oidc.models import MemberFederated


class AddClientOidc:
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        help = "Add client oidc"
        self.app.cli.command('add_client_oidc', short_help=help)(self.run)

    @click.argument('domain')
    @click.argument('client_id')
    @click.argument('client_secret')
    def run(self, domain, client_id, client_secret):
        member = MemberFederated.query.filter_by(domain=domain).first()
        if not member:
            return

        member.client_id = client_id
        member.client_secret = client_secret

        db.session.commit()
