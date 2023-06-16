import click

from ereuse_devicehub.db import db
from ereuse_devicehub.modules.oidc.models import MemberFederated


class AddMember:
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        help = "Add member to the federated net"
        self.app.cli.command('dlt_add_member', short_help=help)(self.run)

    @click.argument('dlt_id_provider')
    @click.argument('domain')
    def run(self, dlt_id_provider, domain):
        member = MemberFederated.query.filter_by(domain=domain).first()
        if member:
            return

        member = MemberFederated(domain=domain, dlt_id_provider=dlt_id_provider)

        db.session.add(member)
        db.session.commit()
