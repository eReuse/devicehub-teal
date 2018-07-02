from pathlib import Path

import click
import click_spinner
import yaml
from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.event.models import Snapshot
from ereuse_devicehub.resources.inventory import Inventory
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.resources.user import User


class Dummy:
    SNAPSHOTS = (
        'workbench-server-1',
        'computer-monitor'
    )
    TAGS = (
        'tag1',
        'tag2',
        'tag3'
    )

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.app.cli.command('dummy',
                             short_help='Creates dummy devices and users.')(self.run)

    @click.confirmation_option(prompt='This command deletes the DB in the process. '
                                      'Do you want to continue?')
    def run(self):
        print('Preparing the database...'.ljust(30), end='')
        with click_spinner.spinner():
            self.app.init_db(erase=True)
            user = self.user_client('user@dhub.com', '1234')
            user.post(res=Tag, query=[('ids', i) for i in self.TAGS], data={})
        files = tuple(Path(__file__).parent.joinpath('files').iterdir())
        print('done.')
        with click.progressbar(files, label='Creating devices...'.ljust(28)) as bar:
            for path in bar:
                with path.open() as f:
                    snapshot = yaml.load(f)
                user.post(res=Snapshot, data=snapshot)
        inventory, _ = user.get(res=Inventory)
        assert len(inventory['devices'])
        print('⭐ Done.')

    def user_client(self, email: str, password: str):
        user = User(email=email, password=password)
        db.session.add(user)
        db.session.commit()
        client = UserClient(application=self.app,
                            response_wrapper=self.app.response_class,
                            email=user.email,
                            password=password)
        client.user, _ = client.login(client.email, client.password)
        return client
