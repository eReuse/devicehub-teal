import itertools
import json
import uuid
from pathlib import Path

import click
import click_spinner
import jwt
import yaml
from ereuse_devicehub.ereuse_utils.test import ANY
from ereuse_devicehub import ereuse_utils

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.parser.models import SnapshotsLog
from ereuse_devicehub.resources.action import models as m
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.enums import SessionType
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.resources.user import User
from ereuse_devicehub.resources.user.models import Session


class Dummy:
    TAGS = ('tag1', 'tag2', 'tag3')
    """Tags to create."""
    ET = (
        ('DT-AAAAA', 'A0000000000001'),
        ('DT-BBBBB', 'A0000000000002'),
        ('DT-CCCCC', 'A0000000000003'),
        ('DT-BRRAB', '04970DA2A15984'),
        ('DT-XXXXX', '04e4bc5af95980'),
    )
    """eTags to create."""
    ORG = 'eReuse.org CAT', '-t', 'G-60437761', '-c', 'ES'
    """An organization to create."""

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.app.cli.command('dummy', short_help='Creates dummy devices and users.')(
            self.run
        )

    @click.option(
        '--tag-url',
        '-tu',
        type=ereuse_utils.cli.URL(scheme=True, host=True, path=False),
        default='http://localhost:8081',
        help='The base url (scheme and host) of the tag provider.',
    )
    @click.option(
        '--tag-token',
        '-tt',
        type=click.UUID,
        default='899c794e-1737-4cea-9232-fdc507ab7106',
        help='The token provided by the tag provider. It is an UUID.',
    )
    @click.confirmation_option(
        prompt='This command (re)creates the DB from scratch.'
        'Do you want to continue?'
    )
    def run(self, tag_url, tag_token):
        runner = self.app.test_cli_runner()
        self.app.init_db(
            'Dummy', 'ACME', 'acme-id', tag_url, tag_token, erase=True, common=True
        )
        print('Creating stuff...'.ljust(30), end='')
        assert SnapshotsLog.query.filter().all() == []
        with click_spinner.spinner():
            out = runner.invoke('org', 'add', *self.ORG).output
            org_id = json.loads(out)['id']
            user1 = self.user_client('user@dhub.com', '1234', 'user1')
            user2 = self.user_client('user2@dhub.com', '1234', 'user2')
            user3 = self.user_client('user3@dhub.com', '1234', 'user3')
            user4 = self.user_client('user4@dhub.com', '1234', 'user4')

            # todo put user's agent into Org
            for id in self.TAGS:
                user1.post({'id': id}, res=Tag)
            for id, sec in self.ET:
                runner.invoke(
                    'tag',
                    'add',
                    id,
                    '-p',
                    'https://t.devicetag.io',
                    '-s',
                    sec,
                    '-u',
                    user1.user["id"],
                    '-o',
                    org_id,
                )
            # create tag for pc-laudem
            runner.invoke(
                'tag',
                'add',
                'tagA',
                '-p',
                'https://t.devicetag.io',
                '-u',
                user1.user["id"],
                '-s',
                'tagA-secondary',
            )
        files = tuple(Path(__file__).parent.joinpath('files').iterdir())
        print('done.')
        sample_pc = None  # We treat this one as a special sample for demonstrations
        pcs = set()
        with click.progressbar(files, label='Creating devices...'.ljust(28)) as bar:
            for path in bar:
                with path.open() as f:
                    snapshot = yaml.load(f)
                    if snapshot['device']['type'] in ['Desktop', 'Laptop']:
                        snapshot['device']['system_uuid'] = uuid.uuid4()
                s, _ = user1.post(res=m.Snapshot, data=self.json_encode(snapshot))
                if s.get('uuid', None) == 'ec23c11b-80b6-42cd-ac5c-73ba7acddbc4':
                    sample_pc = s['device']['id']
                    sample_pc_devicehub_id = s['device']['devicehubID']
                else:
                    pcs.add(s['device']['id'])
                if (
                    s.get('uuid', None) == 'de4f495e-c58b-40e1-a33e-46ab5e84767e'
                ):  # oreo
                    # Make one hdd ErasePhysical
                    hdd = next(
                        hdd for hdd in s['components'] if hdd['type'] == 'HardDrive'
                    )
                    user1.post(
                        {
                            'type': 'ErasePhysical',
                            'method': 'Shred',
                            'device': hdd['id'],
                        },
                        res=m.Action,
                    )
        assert sample_pc
        print('PC sample is', sample_pc)
        # Link tags and eTags
        for tag, pc in zip(
            (self.TAGS[1], self.TAGS[2], self.ET[0][0], self.ET[1][1]), pcs
        ):
            user1.put({}, res=Tag, item='{}/device/{}'.format(tag, pc), status=204)

        # Perform generic actions
        for pc, model in zip(
            pcs, {m.ToRepair, m.Repair, m.ToPrepare, m.Ready, m.ToPrepare, m.Prepare}
        ):
            user1.post({'type': model.t, 'devices': [pc]}, res=m.Action)

        # Perform a Sell to several devices
        # user1.post(
        # {
        # 'type': m.Sell.t,
        # 'to': user1.user['individuals'][0]['id'],
        # 'devices': list(itertools.islice(pcs, len(pcs) // 2))
        # },
        # res=m.Action)

        lot_user, _ = user1.post({'name': 'LoteStephan'}, res=Lot)

        lot_user2, _ = user2.post({'name': 'LoteSergio'}, res=Lot)

        lot_user3, _ = user3.post({'name': 'LoteManos'}, res=Lot)

        lot_user4, _ = user4.post({'name': 'LoteJordi'}, res=Lot)

        lot, _ = user1.post(
            {},
            res=Lot,
            item='{}/devices'.format(lot_user['id']),
            query=[('id', pc) for pc in itertools.islice(pcs, 1, 4)],
        )
        # assert len(lot['devices'])

        lot2, _ = user2.post(
            {},
            res=Lot,
            item='{}/devices'.format(lot_user2['id']),
            query=[('id', pc) for pc in itertools.islice(pcs, 4, 6)],
        )

        lot3, _ = user3.post(
            {},
            res=Lot,
            item='{}/devices'.format(lot_user3['id']),
            query=[('id', pc) for pc in itertools.islice(pcs, 11, 14)],
        )

        lot4, _ = user4.post(
            {},
            res=Lot,
            item='{}/devices'.format(lot_user4['id']),
            query=[('id', pc) for pc in itertools.islice(pcs, 14, 16)],
        )

        # Keep this at the bottom
        inventory, _ = user1.get(res=Device)
        assert len(inventory['items'])

        # i, _ = user1.get(res=Device, query=[('search', 'intel')])
        # assert len(i['items']) in [14, 12]
        # i, _ = user1.get(res=Device, query=[('search', 'pc')])
        # assert len(i['items']) in [17, 14]

        # Let's create a set of actions for the pc device
        # Make device Ready

        user1.post({'type': m.ToPrepare.t, 'devices': [sample_pc]}, res=m.Action)
        user1.post({'type': m.Prepare.t, 'devices': [sample_pc]}, res=m.Action)
        user1.post({'type': m.Ready.t, 'devices': [sample_pc]}, res=m.Action)
        user1.post(
            {'type': m.Price.t, 'device': sample_pc, 'currency': 'EUR', 'price': 85},
            res=m.Action,
        )

        # todo test reserve
        # user1.post(  # Sell device
        # {
        # 'type': m.Sell.t,
        # 'to': user1.user['individuals'][0]['id'],
        # 'devices': [sample_pc]
        # },
        # res=m.Action)
        # todo Receive

        user1.get(res=Device, item=sample_pc_devicehub_id)  # Test
        anonymous = self.app.test_client()
        html, _ = anonymous.get(res=Device, item=sample_pc_devicehub_id, accept=ANY)
        assert 'hewlett-packard' in html

        # For netbook: to preapre -> torepair -> to dispose -> disposed
        print('⭐ Done.')

    def user_client(self, email: str, password: str, name: str):
        user = User(email=email, password=password)

        user.individuals.add(Person(name=name))
        db.session.add(user)
        session_external = Session(user=user, type=SessionType.External)
        session_internal = Session(user=user, type=SessionType.Internal)
        db.session.add(session_internal)
        db.session.add(session_external)

        db.session.commit()
        client = UserClient(
            self.app, user.email, password, response_wrapper=self.app.response_class
        )
        client.login()
        return client

    def json_encode(self, dev: str) -> dict:
        """Encode json."""
        data = {"type": "Snapshot"}
        data['data'] = jwt.encode(
            dev,
            self.app.config['JWT_PASS'],
            algorithm="HS256",
            json_encoder=ereuse_utils.JSONEncoder,
        )

        return data
