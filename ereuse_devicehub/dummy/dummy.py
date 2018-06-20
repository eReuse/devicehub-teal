from pathlib import Path

import click
import click_spinner
import yaml
from tqdm import tqdm

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.event.models import Snapshot
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
        print('Preparing the database...')
        with click_spinner.spinner():
            self.app.init_db(erase=True)
            user = self.user_client('user@dhub.com', '1234')
            user.post(res=Tag, query=[('ids', i) for i in self.TAGS], data={})
        print('Creating devices...')
        for file_name in tqdm(self.SNAPSHOTS):
            snapshot = self.file(file_name)
            user.post(res=Snapshot, data=snapshot)
        print('Done :-)')

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

    def file(self, name: str):
        with Path(__file__) \
                .parent \
                .joinpath('files') \
                .joinpath(name + '.snapshot.yaml').open() as f:
            return yaml.load(f)
