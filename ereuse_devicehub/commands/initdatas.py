from uuid import uuid4

from boltons.urlutils import URL
from decouple import config

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.inventory.model import Inventory
from ereuse_devicehub.resources.user.models import User


class InitDatas:
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.schema = app.config.get('DB_SCHEMA')
        self.email = config('EMAIL_DEMO')
        self.name = self.email.split('@')[0] if self.email else None
        self.password = config('PASSWORD_DEMO')
        self.app.cli.command(
            'initdata', short_help='Save a minimum structure of datas.'
        )(self.run)

    def run(self):
        inv = Inventory(
            id=self.schema,
            name="usody",
            tag_provider=URL('http://localhost:8081'),
            tag_token=uuid4(),
            org_id=uuid4(),
        )

        db.session.add(inv)
        db.session.commit()

        if self.email:
            user = User(email=self.email, password=self.password)
            user.individuals.add(Person(name=self.name))
            db.session.add(user)

            db.session.commit()
