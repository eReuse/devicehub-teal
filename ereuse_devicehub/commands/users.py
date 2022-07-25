import click

from ereuse_devicehub import auth
from ereuse_devicehub.resources.user.models import User


class GetToken:

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.app.cli.command('get_token', short_help='show the user token.')(
            self.run
        )

    @click.argument('email')
    def run(self, email):
        user = User.query.filter_by(email=email, active=True, phantom=False).one_or_none()
        if user:
            print(auth.Auth.encode(user.token))
