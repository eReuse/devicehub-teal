from datetime import datetime, timedelta
from distutils.version import StrictVersion
from typing import List, Tuple
from uuid import uuid4

import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.exceptions import NeedsId
from ereuse_devicehub.resources.device.models import Device, Microtower, SolidStateDrive
from ereuse_devicehub.resources.device.sync import MismatchBetweenTagsAndHid
from ereuse_devicehub.resources.enums import Bios, RatingSoftware, SnapshotSoftware
from ereuse_devicehub.resources.event.models import EraseBasic, Event, Snapshot, SnapshotRequest, \
    WorkbenchRate
from ereuse_devicehub.resources.tag import Tag
from ereuse_devicehub.resources.user.models import User
from tests.conftest import file


def assert_similar_device(device1: dict, device2: dict):
    """
    Like :class:`ereuse_devicehub.resources.device.models.Device.
    is_similar()` but adapted for testing.
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
                       event_types: Tuple[str] = tuple(),
                       perform_second_snapshot=True) -> dict:
    """
        Performs a Snapshot and then checks if the result is ok:

        - There have been performed the types of events and in the same
          order as described in the passed-in ``event_types``.
        - The inputted devices are similar to the resulted ones.
        - There is no Remove event after the first Add.
        - All input components are now inside the parent device.

        Optionally, it can perform a second Snapshot which should
        perform an exact result, except for the events.

        :return: The last resulting snapshot.
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
    if input_snapshot.get('components', None):
        assert_similar_components(input_snapshot['components'], snapshot['components'])
    assert all(c['parent'] == snapshot['device']['id'] for c in snapshot['components']), \
        'Components must be in their parent'
    if perform_second_snapshot:
        if 'uuid' in input_snapshot:
            input_snapshot['uuid'] = uuid4()
        return snapshot_and_check(user, input_snapshot, event_types, perform_second_snapshot=False)
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
                        software=SnapshotSoftware.DesktopApp,
                        elapsed=timedelta(seconds=25))
    snapshot.device = device
    snapshot.request = SnapshotRequest(request={'foo': 'bar'})
    snapshot.events.add(WorkbenchRate(processor=0.1,
                                      ram=1.0,
                                      bios=Bios.A,
                                      labelling=False,
                                      graphic_card=0.1,
                                      data_storage=4.1,
                                      algorithm_software=RatingSoftware.Ereuse,
                                      algorithm_version=StrictVersion('1.0'),
                                      device=device))
    db.session.add(snapshot)
    db.session.commit()
    device = Microtower.query.one()  # type: Microtower
    e1, e2 = device.events
    assert isinstance(e1, Snapshot), 'Creation order must be preserved: 1. snapshot, 2. WR'
    assert isinstance(e2, WorkbenchRate)
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
    Tests the post snapshot endpoint (validation, etc), data correctness,
    and relationship correctness.
    """
    snapshot = snapshot_and_check(user, file('basic.snapshot'),
                                  event_types=('WorkbenchRate',),
                                  perform_second_snapshot=False)
    assert snapshot['software'] == 'Workbench'
    assert snapshot['version'] == '11.0'
    assert snapshot['uuid'] == 'f5efd26e-8754-46bc-87bf-fbccc39d60d9'
    assert snapshot['elapsed'] == 4
    assert snapshot['author']['id'] == user.user['id']
    assert 'events' not in snapshot['device']
    assert 'author' not in snapshot['device']
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert snapshot['components'] == device['components']

    assert tuple(c['type'] for c in snapshot['components']) == ('GraphicCard', 'RamModule')
    rate, _ = user.get(res=Event, item=snapshot['events'][0]['id'])
    assert rate['device']['id'] == snapshot['device']['id']
    assert rate['components'] == snapshot['components']
    assert rate['snapshot']['id'] == snapshot['id']


def test_snapshot_component_add_remove(user: UserClient):
    """
    Tests adding and removing components and some don't generate HID.
    All computers generate HID.
    """

    def get_events_info(events: List[dict]) -> tuple:
        return tuple(
            (
                e['type'],
                [c['serialNumber'] for c in e['components']]
            )
            for e in user.get_many(res=Event, resources=events, key='id')
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
    snapshot2 = snapshot_and_check(user, s2, event_types=('Remove',),
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
    assert tuple(e['type'] for e in pc2['events']) == ('Snapshot',)
    # p1c2s has two Snapshots, a Remove and an Add
    p1c2s, _ = user.get(res=Device, item=pc2['components'][0]['id'])
    assert tuple(e['type'] for e in p1c2s['events']) == ('Snapshot', 'Snapshot', 'Remove')

    # We register the first device again, but removing motherboard
    # and moving processor from the second device to the first.
    # We have created 1 Remove (from PC2's processor back to PC1)
    # PC 0: p1c2s, p1c3s. PC 1: p2c1s
    s3 = file('3-first-device-but-removing-motherboard-and-adding-processor-from-2.snapshot')
    snapshot_and_check(user, s3, ('Remove',), perform_second_snapshot=False)
    pc1, _ = user.get(res=Device, item=pc1_id)
    pc2, _ = user.get(res=Device, item=pc2_id)
    # PC1
    assert {c['serialNumber'] for c in pc1['components']} == {'p1c2s', 'p1c3s'}
    assert all(c['parent'] == pc1_id for c in pc1['components'])
    assert tuple(get_events_info(pc1['events'])) == (
        # id, type, components, snapshot
        ('Snapshot', ['p1c1s', 'p1c2s', 'p1c3s']),  # first Snapshot1
        ('Remove', ['p1c2s']),  # Remove Processor in Snapshot2
        ('Snapshot', ['p1c2s', 'p1c3s'])  # This Snapshot3
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
    assert tuple(get_events_info(p1c2s['events'])) == (
        ('Snapshot', ['p1c1s', 'p1c2s', 'p1c3s']),  # First Snapshot to PC1
        ('Snapshot', ['p1c2s', 'p2c1s']),  # Second Snapshot to PC2
        ('Remove', ['p1c2s']),  # ...which caused p1c2s to be removed form PC1
        ('Snapshot', ['p1c2s', 'p1c3s']),  # The third Snapshot to PC1
        ('Remove', ['p1c2s'])  # ...which caused p1c2 to be removed from PC2
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
    assert get_events_info(pc1['events'])[-1] == ('Snapshot', ['p1c3s', 'p1c4s'])
    # PC2
    # We haven't changed PC2
    assert tuple(c['serialNumber'] for c in pc2['components']) == ('p2c1s',)
    assert all(c['parent'] == pc2_id for c in pc2['components'])


def _test_snapshot_computer_no_hid(user: UserClient):
    """
    Tests inserting a computer that doesn't generate a HID, neither
    some of its components.
    """
    # PC with 2 components. PC doesn't have HID and neither 1st component
    s = file('basic.snapshot')
    del s['device']['model']
    del s['components'][0]['model']
    user.post(s, res=Snapshot, status=NeedsId)
    # The system tells us that it could not register the device because
    # the device (computer) cannot generate a HID.
    # In such case we need to specify an ``id`` so the system can
    # recognize the device. The ``id`` can reference to the same
    # device, it already existed in the DB, or to a placeholder,
    # if the device is new in the DB.
    user.post(s, res=Device)
    s['device']['id'] = 1  # Assign the ID of the placeholder
    user.post(s, res=Snapshot)


def test_snapshot_mismatch_id():
    """Tests uploading a device with an ID from another device."""
    # Note that this won't happen as in this new algorithm_version
    # the ID is not used in the Snapshot process
    pass


def test_snapshot_tag_inner_tag(tag_id: str, user: UserClient, app: Devicehub):
    """Tests a posting Snapshot with a local tag."""
    b = file('basic.snapshot')
    b['device']['tags'] = [{'type': 'Tag', 'id': tag_id}]
    snapshot_and_check(user, b, event_types=('WorkbenchRate',))
    with app.app_context():
        tag, *_ = Tag.query.all()  # type: Tag
        assert tag.device_id == 1, 'Tag should be linked to the first device'


def test_snapshot_tag_inner_tag_mismatch_between_tags_and_hid(user: UserClient, tag_id: str):
    """Ensures one device cannot 'steal' the tag from another one."""
    pc1 = file('basic.snapshot')
    pc1['device']['tags'] = [{'type': 'Tag', 'id': tag_id}]
    user.post(pc1, res=Snapshot)
    pc2 = file('1-device-with-components.snapshot')
    user.post(pc2, res=Snapshot)  # PC2 uploads well
    pc2['device']['tags'] = [{'type': 'Tag', 'id': tag_id}]  # Set tag from pc1 to pc2
    user.post(pc2, res=Snapshot, status=MismatchBetweenTagsAndHid)


def test_erase(user: UserClient):
    """Tests a Snapshot with EraseSectors."""
    s = file('erase-sectors.snapshot')
    snapshot = snapshot_and_check(user, s, ('EraseSectors',), perform_second_snapshot=True)
    storage, *_ = snapshot['components']
    assert storage['type'] == 'SolidStateDrive', 'Components must be ordered by input order'
    storage, _ = user.get(res=SolidStateDrive, item=storage['id'])  # Let's get storage events too
    # order: creation time descending
    _snapshot1, erasure1, _snapshot2, erasure2 = storage['events']
    assert erasure1['type'] == erasure2['type'] == 'EraseSectors'
    assert _snapshot1['type'] == _snapshot2['type'] == 'Snapshot'
    assert snapshot == user.get(res=Event, item=_snapshot2['id'])[0]
    erasure, _ = user.get(res=EraseBasic, item=erasure1['id'])
    assert len(erasure['steps']) == 2
    assert erasure['steps'][0]['startTime'] == '2018-06-01T08:15:00+00:00'
    assert erasure['steps'][0]['endTime'] == '2018-06-01T09:16:00+00:00'
    assert erasure['steps'][1]['startTime'] == '2018-06-01T08:16:00+00:00'
    assert erasure['steps'][1]['endTime'] == '2018-06-01T09:17:00+00:00'
    assert erasure['device']['id'] == storage['id']
    for step in erasure['steps']:
        assert step['type'] == 'StepZero'
        assert step['error'] is False
        assert step['secureRandomSteps'] == 1
        assert step['cleanWithZeros'] is True
        assert 'num' not in step


def test_snapshot_computer_monitor(user: UserClient):
    s = file('computer-monitor.snapshot')
    snapshot_and_check(user, s, event_types=('AppRate',))


def test_snapshot_components_none():
    """
    Tests that a snapshot without components does not
    remove them from the computer.
    """
    # todo test
    pass


def test_snapshot_components_empty():
    """
    Tests that a snapshot whose components are an empty list remove
    all its components.
    """
