import json

import click

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.models import User


class RegisterUserDlt:
    #  "Operator", "Verifier" or "Witness"

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        help = "Register user in Dlt with params: email password rols"
        self.app.cli.command('dlt_register_user', short_help=help)(self.run)

    @click.argument('email')
    @click.argument('password')
    @click.argument('rols')
    def run(self, email, password, rols):
        if not rols:
            rols = "Operator"
        user = User.query.filter_by(email=email).one()

        token_dlt = user.set_new_dlt_keys(password)
        result = user.allow_permitions(api_token=token_dlt, rols=rols)
        rols = user.get_rols(token_dlt=token_dlt)
        rols = [k for k, v in rols]
        user.rols_dlt = json.dumps(rols)

        db.session.commit()

        return result, rols
