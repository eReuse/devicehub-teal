import itertools
import json
from pathlib import Path
from typing import Set

import click
import click_spinner
import yaml
from ereuse_utils.test import ANY

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.event import models as m
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
        ('A0000000000003', 'DT-CCCCC'),
        ('04970DA2A15984', 'DT-BRRAB')
    )
    """eTags to create."""
    ORG = 'eReuse.org CAT', '-t', 'G-60437761', '-c', 'ES'
    """An organization to create."""

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.app.cli.command('dummy', short_help='Creates dummy devices and users.')(self.run)

    @click.confirmation_option(prompt='This command (re)creates the DB from scratch.'
                                      'Do you want to continue?')
    def run(self):
        runner = self.app.test_cli_runner()
        self.app.init_db(erase=True)
        print('Creating stuff...'.ljust(30), end='')
        with click_spinner.spinner():
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
            # create tag for pc-laudem
            runner.invoke(args=[
                'create-tag', 'tagA',
                '-p', 'https://t.devicetag.io',
                '-s', 'tagA-secondary'
            ],
                catch_exceptions=False)
        files = tuple(Path(__file__).parent.joinpath('files').iterdir())
        print('done.')
        sample_pc = None  # We treat this one as a special sample for demonstrations
        pcs = set()  # type: Set[int]
        with click.progressbar(files, label='Creating devices...'.ljust(28)) as bar:
            for path in bar:
                with path.open() as f:
                    snapshot = yaml.load(f)
                s, _ = user.post(res=m.Snapshot, data=snapshot)
                if s.get('uuid', None) == 'ec23c11b-80b6-42cd-ac5c-73ba7acddbc4':
                    sample_pc = s['device']['id']
                else:
                    pcs.add(s['device']['id'])
                if s.get('uuid', None) == 'de4f495e-c58b-40e1-a33e-46ab5e84767e': # oreo
                    # Make one hdd ErasePhysical
                    hdd = next(hdd for hdd in s['components'] if hdd['type'] == 'HardDrive')
                    user.post({'type': 'ErasePhysical', 'method': 'Shred', 'device': hdd['id']}, res=m.Event)
        assert sample_pc
        print('PC sample is', sample_pc)
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

        parent, _ = user.post(({'name': 'Parent'}), res=Lot)
        child, _ = user.post(({'name': 'Child'}), res=Lot)
        parent, _ = user.post({},
                              res=Lot,
                              item='{}/children'.format(parent['id']),
                              query=[('id', child['id'])])

        lot, _ = user.post({},
                           res=Lot,
                           item='{}/devices'.format(child['id']),
                           query=[('id', pc) for pc in itertools.islice(pcs, len(pcs) // 3)])
        assert len(lot['devices'])

        # Keep this at the bottom
        inventory, _ = user.get(res=Device)
        assert len(inventory['items'])

        i, _ = user.get(res=Device, query=[('search', 'intel')])
        assert len(i['items']) == 12
        i, _ = user.get(res=Device, query=[('search', 'pc')])
        assert len(i['items']) == 13

        # Let's create a set of events for the pc device
        # Make device Ready

        user.post({'type': m.ToPrepare.t, 'devices': [sample_pc]}, res=m.Event)
        user.post({'type': m.Prepare.t, 'devices': [sample_pc]}, res=m.Event)
        user.post({'type': m.ReadyToUse.t, 'devices': [sample_pc]}, res=m.Event)
        user.post({'type': m.Price.t, 'device': sample_pc, 'currency': 'EUR', 'price': 85},
                  res=m.Event)
        # todo test reserve
        user.post(  # Sell device
            {
                'type': m.Sell.t,
                'to': user.user['individuals'][0]['id'],
                'devices': [sample_pc]
            },
            res=m.Event)
        # todo Receive

        user.get(res=Device, item=sample_pc)  # Test
        anonymous = self.app.test_client()
        html, _ = anonymous.get(res=Device, item=sample_pc, accept=ANY)
        assert 'intel core2 duo cpu' in html

        # For netbook: to preapre -> torepair -> to dispose -> disposed
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
