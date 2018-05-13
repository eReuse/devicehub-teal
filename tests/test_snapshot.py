from datetime import datetime, timedelta
from typing import List
from uuid import uuid4

import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.models import Device, Microtower
from ereuse_devicehub.resources.event.models import Appearance, Bios, Event, Functionality, \
    Snapshot, SnapshotRequest, SoftwareType
from ereuse_devicehub.resources.user.models import User
from tests.conftest import file


def assert_similar_device(device1: dict, device2: dict):
    """
    Like Model.is_similar() but adapted for testing.
    """
    assert isinstance(device1, dict) and device1
    assert isinstance(device2, dict) and device2
    for key in 'serialNumber', 'model', 'manufacturer', 'type':
        assert device1.get(key, None) == device2.get(key, None)


def assert_similar_components(components1: List[dict], components2: List[dict]):
    """
    Asserts that the components in components1 are
    similar than the components in components2.
    """
    assert len(components1) == len(components2)
    for c1, c2 in zip(components1, components2):
        assert_similar_device(c1, c2)


def snapshot_and_check(user: UserClient,
                       input_snapshot: dict,
                       event_types: tuple or list = tuple(),
                       perform_second_snapshot=True) -> dict:
    """
        P
    """
    snapshot, _ = user.post(res=Snapshot, data=input_snapshot)
    assert tuple(e['type'] for e in snapshot['events']) == event_types
    # Ensure there is no Remove event after the first Add
    found_add = False
    for event in snapshot['events']:
        if event['type'] == 'Add':
            found_add = True
        if found_add:
            assert event['type'] != 'Receive', 'All Remove events must be before the Add ones'
    assert input_snapshot['device']
    assert_similar_device(input_snapshot['device'], snapshot['device'])
    assert_similar_components(input_snapshot['components'], snapshot['components'])
    assert all(c['parent'] == snapshot['device']['id'] for c in snapshot['components']), \
        'Components must be in their parent'
    if perform_second_snapshot:
        input_snapshot['uuid'] = uuid4()
        return snapshot_and_check(user, input_snapshot, perform_second_snapshot=False)
    else:
        return snapshot


@pytest.mark.usefixtures('auth_app_context')
def test_snapshot_model():
    """
    Tests creating a Snapshot with its relationships ensuring correct
    DB mapping.
    """
    device = Microtower(serial_number='a1')
    # noinspection PyArgumentList
    snapshot = Snapshot(uuid=uuid4(),
                        date=datetime.now(),
                        version='1.0',
                        software=SoftwareType.DesktopApp,
                        appearance=Appearance.A,
                        appearance_score=5,
                        functionality=Functionality.A,
                        functionality_score=5,
                        labelling=False,
                        bios=Bios.C,
                        condition=5,
                        elapsed=timedelta(seconds=25))
    snapshot.device = device
    snapshot.request = SnapshotRequest(request={'foo': 'bar'})

    db.session.add(snapshot)
    db.session.commit()
    device = Microtower.query.one()  # type: Microtower
    assert device.events_one[0].type == Snapshot.__name__
    db.session.delete(device)
    db.session.commit()
    assert Snapshot.query.one_or_none() is None
    assert SnapshotRequest.query.one_or_none() is None
    assert User.query.one() is not None
    assert Microtower.query.one_or_none() is None
    assert Device.query.one_or_none() is None


def test_snapshot_schema(app: Devicehub):
    with app.app_context():
        s = file('basic.snapshot')
        app.resources['Snapshot'].schema.load(s)


def test_snapshot_post(user: UserClient):
    """
    Tests the post snapshot endpoint (validation, etc)
    and data correctness.
    """
    snapshot = snapshot_and_check(user, file('basic.snapshot'), perform_second_snapshot=False)
    assert snapshot['software'] == 'Workbench'
    assert snapshot['version'] == '11.0'
    assert snapshot['uuid'] == 'f5efd26e-8754-46bc-87bf-fbccc39d60d9'
    assert snapshot['events'] == []
    assert snapshot['elapsed'] == 4
    assert snapshot['author']['id'] == user.user['id']
    assert 'events' not in snapshot['device']
    assert 'author' not in snapshot['device']


def test_snapshot_add_remove(user: UserClient):
    def get_events_info(events: List[dict]) -> tuple:
        return tuple(
            (
                e['id'],
                e['type'],
                [c['serialNumber'] for c in e['components']],
                e.get('snapshot', {}).get('id', None)
            )
            for e in (user.get(res=Event, item=e['id'])[0] for e in events)
        )

    # We add the first device (2 times). The distribution of components
    # (represented with their S/N) should be:
    # PC 1: p1c1s, p1c2s, p1c3s. PC 2: ø
    s1 = file('1-device-with-components.snapshot')
    snapshot1 = snapshot_and_check(user, s1, perform_second_snapshot=False)
    pc1_id = snapshot1['device']['id']
    pc1, _ = user.get(res=Device, item=pc1_id)
    # Parent contains components
    assert tuple(c['serialNumber'] for c in pc1['components']) == ('p1c1s', 'p1c2s', 'p1c3s')
    # Components contain parent
    assert all(c['parent'] == pc1_id for c in pc1['components'])
    # pc has Snapshot as event
    assert len(pc1['events']) == 1
    assert pc1['events'][0]['type'] == Snapshot.t
    # p1c1s has Snapshot
    p1c1s, _ = user.get(res=Device, item=pc1['components'][0]['id'])
    assert tuple(e['type'] for e in p1c1s['events']) == ('Snapshot',)

    # We register a new device
    # It has the processor of the first one (p1c2s)
    # PC 1: p1c1s, p1c3s. PC 2: p2c1s, p1c2s
    # Events PC1: Snapshot, Remove. PC2: Snapshot
    s2 = file('2-second-device-with-components-of-first.snapshot')
    # num_events = 2 = Remove, Add
    snapshot2 = snapshot_and_check(user, s2, event_types=('Remove', ),
                                   perform_second_snapshot=False)
    pc2_id = snapshot2['device']['id']
    pc1, _ = user.get(res=Device, item=pc1_id)
    pc2, _ = user.get(res=Device, item=pc2_id)
    # PC1
    assert tuple(c['serialNumber'] for c in pc1['components']) == ('p1c1s', 'p1c3s')
    assert all(c['parent'] == pc1_id for c in pc1['components'])
    assert tuple(e['type'] for e in pc1['events']) == ('Snapshot', 'Remove')
    # PC2
    assert tuple(c['serialNumber'] for c in pc2['components']) == ('p1c2s', 'p2c1s')
    assert all(c['parent'] == pc2_id for c in pc2['components'])
    assert tuple(e['type'] for e in pc2['events']) == ('Snapshot', )
    # p1c2s has two Snapshots, a Remove and an Add
    p1c2s, _ = user.get(res=Device, item=pc2['components'][0]['id'])
    assert tuple(e['type'] for e in p1c2s['events']) == ('Snapshot', 'Snapshot', 'Remove')

    # We register the first device again, but removing motherboard
    # and moving processor from the second device to the first.
    # We have created 1 Remove (from PC2's processor back to PC1)
    # PC 0: p1c2s, p1c3s. PC 1: p2c1s
    s3 = file('3-first-device-but-removing-motherboard-and-adding-processor-from-2.snapshot')
    snapshot_and_check(user, s3, ('Remove', ), perform_second_snapshot=False)
    pc1, _ = user.get(res=Device, item=pc1_id)
    pc2, _ = user.get(res=Device, item=pc2_id)
    # PC1
    assert {c['serialNumber'] for c in pc1['components']} == {'p1c2s', 'p1c3s'}
    assert all(c['parent'] == pc1_id for c in pc1['components'])
    assert get_events_info(pc1['events']) == (
        # id, type, components, snapshot
        (1, 'Snapshot', ['p1c1s', 'p1c2s', 'p1c3s'], None),  # first Snapshot1
        (3, 'Remove', ['p1c2s'], 2),  # Remove Processor in Snapshot2
        (4, 'Snapshot', ['p1c2s', 'p1c3s'], None)  # This Snapshot3
    )
    # PC2
    assert tuple(c['serialNumber'] for c in pc2['components']) == ('p2c1s',)
    assert all(c['parent'] == pc2_id for c in pc2['components'])
    assert tuple(e['type'] for e in pc2['events']) == (
        'Snapshot',  # Second Snapshot
        'Remove'  # the processor we added in 2.
    )
    # p1c2s has Snapshot, Remove and Add
    p1c2s, _ = user.get(res=Device, item=pc1['components'][0]['id'])
    assert get_events_info(p1c2s['events']) == (
        (1, 'Snapshot', ['p1c1s', 'p1c2s', 'p1c3s'], None),  # First Snapshot to PC1
        (2, 'Snapshot', ['p1c2s', 'p2c1s'], None),  # Second Snapshot to PC2
        (3, 'Remove', ['p1c2s'], 2),  # ...which caused p1c2s to be removed form PC1
        (4, 'Snapshot', ['p1c2s', 'p1c3s'], None),  # The third Snapshot to PC1
        (5, 'Remove', ['p1c2s'], 4)  # ...which caused p1c2 to be removed from PC2
    )

    # We register the first device but without the processor,
    # adding a graphic card and adding a new component
    s4 = file('4-first-device-but-removing-processor.snapshot-and-adding-graphic-card')
    snapshot_and_check(user, s4, perform_second_snapshot=False)
    pc1, _ = user.get(res=Device, item=pc1_id)
    pc2, _ = user.get(res=Device, item=pc2_id)
    # PC 0: p1c3s, p1c4s. PC1: p2c1s
    assert {c['serialNumber'] for c in pc1['components']} == {'p1c3s', 'p1c4s'}
    assert all(c['parent'] == pc1_id for c in pc1['components'])
    # This last Snapshot only
    assert get_events_info(pc1['events'])[-1] == (6, 'Snapshot', ['p1c3s', 'p1c4s'], None)
    # PC2
    # We haven't changed PC2
    assert tuple(c['serialNumber'] for c in pc2['components']) == ('p2c1s',)
    assert all(c['parent'] == pc2_id for c in pc2['components'])
