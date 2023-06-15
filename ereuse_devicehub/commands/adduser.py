import click

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.user.models import User


class AddUser:
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.schema = app.config.get('DB_SCHEMA')
        self.app.cli.command('adduser', short_help='add a user.')(self.run)

    @click.argument('email')
    @click.argument('password')
    def run(self, email, password):
        name = email.split('@')[0]

        user = User(email=email, password=password)
        user.individuals.add(Person(name=name))
        db.session.add(user)

        db.session.commit()
