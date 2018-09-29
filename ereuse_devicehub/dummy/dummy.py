import itertools
import json
from pathlib import Path
from typing import Set

import click
import click_spinner
import yaml

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.event import models as m
from ereuse_devicehub.resources.inventory import Inventory
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.resources.user import User


class Dummy:
    TAGS = (
        'tag1',
        'tag2',
        'tag3'
    )
    """Tags to create."""
    ET = (
        ('A0000000000001', 'DT-AAAAA'),
        ('A0000000000002', 'DT-BBBBB'),
    )
    """eTags to create."""
    ORG = 'eReuse.org CAT', 'G-60437761', 'ES'
    """An organization to create."""

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.app.cli.command('dummy',
                             short_help='Creates dummy devices and users.')(self.run)

    @click.confirmation_option(prompt='This command (re)creates the DB from scratch.'
                                      'Do you want to continue?')
    def run(self):
        print('Preparing the database...'.ljust(30), end='')
        runner = self.app.test_cli_runner()
        with click_spinner.spinner():
            self.app.init_db(erase=True)
            out = runner.invoke(args=['create-org', *self.ORG], catch_exceptions=False).output
            org_id = json.loads(out)['id']
            user = self.user_client('user@dhub.com', '1234')
            # todo put user's agent into Org
            for id in self.TAGS:
                user.post({'id': id}, res=Tag)
            for id, sec in self.ET:
                runner.invoke(args=[
                    'create-tag', id,
                    '-p', 'https://t.devicetag.io',
                    '-s', sec,
                    '-o', org_id
                ],
                    catch_exceptions=False)
        files = tuple(Path(__file__).parent.joinpath('files').iterdir())
        print('done.')
        pcs = set()  # type: Set[int]
        with click.progressbar(files, label='Creating devices...'.ljust(28)) as bar:
            for path in bar:
                with path.open() as f:
                    snapshot = yaml.load(f)
                s, _ = user.post(res=m.Snapshot, data=snapshot)
                pcs.add(s['device']['id'])

        # Link tags and eTags
        for tag, pc in zip((self.TAGS[1], self.TAGS[2], self.ET[0][0], self.ET[1][1]), pcs):
            user.put({}, res=Tag, item='{}/device/{}'.format(tag, pc), status=204)

        # Perform generic events
        for pc, model in zip(pcs,
                             {m.ToRepair, m.Repair, m.ToPrepare, m.ReadyToUse, m.ToPrepare,
                              m.Prepare}):
            user.post({'type': model.t, 'devices': [pc]}, res=m.Event)

        # Perform a Sell to several devices
        user.post(
            {
                'type': m.Sell.t,
                'to': user.user['individuals'][0]['id'],
                'devices': list(itertools.islice(pcs, len(pcs) // 2))
            },
            res=m.Event)

        from tests.test_lot import test_post_add_children_view
        child_id = test_post_add_children_view(user)

        lot, _ = user.post({},
                           res=Lot,
                           item='{}/devices'.format(child_id),
                           query=[('id', pc) for pc in itertools.islice(pcs, len(pcs) // 3)])
        assert len(lot['devices'])

        # Keep this at the bottom
        inventory, _ = user.get(res=Inventory)
        assert len(inventory['devices'])
        assert len(inventory['lots'])

        i, _ = user.get(res=Inventory, query=[('search', 'intel')])
        assert len(i['devices']) == 10
        i, _ = user.get(res=Inventory, query=[('search', 'pc')])
        assert len(i['devices']) == 11
        print('⭐ Done.')

    def user_client(self, email: str, password: str):
        user = User(email=email, password=password)
        user.individuals.add(Person(name='Timmy'))
        db.session.add(user)
        db.session.commit()
        client = UserClient(self.app, user.email, password,
                            response_wrapper=self.app.response_class)
        client.login()
        return client
