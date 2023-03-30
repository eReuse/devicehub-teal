import json
import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from operator import itemgetter
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4

import pytest
from boltons import urlutils

from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.ereuse_utils.test import ANY
from ereuse_devicehub.parser.models import SnapshotsLog
from ereuse_devicehub.resources.action.models import (
    Action,
    BenchmarkDataStorage,
    BenchmarkProcessor,
    EraseSectors,
    Ready,
    Snapshot,
    SnapshotRequest,
    VisualTest,
)
from ereuse_devicehub.resources.action.views.snapshot import save_json
from ereuse_devicehub.resources.device import models as m
from ereuse_devicehub.resources.device.models import Device, SolidStateDrive
from ereuse_devicehub.resources.documents import documents
from ereuse_devicehub.resources.enums import ComputerChassis, SnapshotSoftware
from ereuse_devicehub.resources.tag import Tag
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.teal.marshmallow import ValidationError
from tests import conftest
from tests.conftest import file, file_json, json_encode, yaml2json


@pytest.mark.mvp
@pytest.mark.usefixtures('auth_app_context')
def test_snapshot_model():
    """Tests creating a Snapshot with its relationships ensuring correct
    DB mapping.
    """
    device = m.Desktop(serial_number='a1', chassis=ComputerChassis.Tower)
    # noinspection PyArgumentList
    snapshot = Snapshot(
        uuid=uuid4(),
        end_time=datetime.now(timezone.utc),
        version='1.0',
        software=SnapshotSoftware.DesktopApp,
        elapsed=timedelta(seconds=25),
    )
    snapshot.device = device
    snapshot.request = SnapshotRequest(request={'foo': 'bar'})
    db.session.add(snapshot)
    db.session.commit()
    device = m.Desktop.query.one()  # type: m.Desktop
    e1 = device.actions[0]
    assert isinstance(
        e1, Snapshot
    ), 'Creation order must be preserved: 1. snapshot, 2. WR'
    db.session.delete(device)
    db.session.commit()
    assert Snapshot.query.one_or_none() is None
    assert SnapshotRequest.query.one_or_none() is None
    assert User.query.one() is not None
    assert m.Desktop.query.one_or_none() is None
    assert m.Device.query.one_or_none() is None
    # Check properties
    assert device.url == urlutils.URL(
        'http://localhost/devices/%s' % device.devicehub_id
    )


@pytest.mark.mvp
def test_snapshot_schema(app: Devicehub):
    with app.app_context():
        s = yaml2json('basic.snapshot')
        app.resources['Snapshot'].schema.load(s)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_post(user: UserClient):
    """Tests the post snapshot endpoint (validation, etc), data correctness,
    and relationship correctness.
    """
    snapshot = snapshot_and_check(
        user,
        yaml2json('basic.snapshot'),
        action_types=(BenchmarkProcessor.t, VisualTest.t),
        perform_second_snapshot=False,
    )
    assert snapshot['software'] == 'Workbench'
    assert snapshot['version'] == '11.0'
    assert snapshot['uuid'] == 'f5efd26e-8754-46bc-87bf-fbccc39d60d9'
    assert snapshot['elapsed'] == 4
    assert snapshot['author']['id'] == user.user['id']
    assert 'actions' not in snapshot['device']
    assert 'author' not in snapshot['device']
    dev = m.Device.query.filter_by(id=snapshot['device']['id']).one()
    device, _ = user.get(res=m.Device, item=dev.devicehub_id)
    key = itemgetter('serialNumber')
    snapshot['components'].sort(key=key)
    device['components'].sort(key=key)
    assert {(x['id'], x['type']) for x in device['components']} == {
        (x['id'], x['type']) for x in snapshot['components']
    }

    assert {c['type'] for c in snapshot['components']} == {
        m.GraphicCard.t,
        m.RamModule.t,
        m.Processor.t,
    }


@pytest.mark.mvp
def test_same_device_tow_users(user: UserClient, user2: UserClient):
    """Two users can up the same snapshot and the system save 2 computers"""
    user.post(file('basic.snapshot'), res=Snapshot)
    i, _ = user.get(res=m.Device)
    pc = next(d for d in i['items'] if d['type'] == 'Desktop')
    pc_id = pc['id']
    devicehub_id = pc['devicehubID']
    assert i['items'][0]['url'] == f'/devices/{devicehub_id}'

    basic_snapshot = yaml2json('basic.snapshot')
    basic_snapshot['uuid'] = f"{uuid.uuid4()}"
    user2.post(json_encode(basic_snapshot), res=Snapshot)
    i2, _ = user2.get(res=m.Device)
    pc2 = next(d for d in i2['items'] if d['type'] == 'Desktop')
    assert pc['id'] != pc2['id']
    assert pc['ownerID'] != pc2['ownerID']
    assert pc['hid'] == pc2['hid']


@pytest.mark.mvp
def test_snapshot_update_timefield_updated(user: UserClient):
    """
    Tests for check if one computer have the time mark updated when one component of it is updated
    """
    computer1 = yaml2json('1-device-with-components.snapshot')
    snapshot = snapshot_and_check(
        user,
        computer1,
        action_types=(BenchmarkProcessor.t,),
        perform_second_snapshot=False,
    )
    computer2 = yaml2json('2-second-device-with-components-of-first.snapshot')
    pc1_devicehub_id = snapshot['device']['devicehubID']
    pc1, _ = user.get(res=m.Device, item=pc1_devicehub_id)
    assert pc1['updated'] != snapshot['device']['updated']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_power_on_hours(user: UserClient):
    """
    Tests for check if one computer have the time mark updated when one component of it is updated
    """
    snap, _ = user.post(file('asus-eee-1000h.snapshot.bug1857'), res=Snapshot)
    device = m.Device.query.filter_by(id=snap['device']['id']).one()

    for c in device.components:
        if c.type == 'HardDrive':
            hdd = c
            break

    for ac in hdd.actions:
        if ac.type == 'TestDataStorage':
            test_data_storage = ac
            break

    assert (
        test_data_storage.lifetime.total_seconds() / 3600
        == test_data_storage.power_on_hours
    )

    errors = SnapshotsLog.query.filter().all()
    assert len(errors) == 2
    assert str(errors[0].snapshot_uuid) == snap['uuid']
    assert str(errors[1].snapshot.uuid) == snap['uuid']
    assert errors[0].description == 'There is not uuid'
    assert errors[1].description == 'Ok'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_component_add_remove(user: UserClient):
    """Tests adding and removing components and some don't generate HID.
    All computers generate HID.
    """

    def get_actions_info(actions: List[dict]) -> tuple:
        return tuple(
            (e['type'], [c['serialNumber'] for c in e['components']])
            for e in user.get_many(res=Action, resources=actions, key='id')
        )

    # We add the first device (2 times). The distribution of components
    # (represented with their S/N) should be:
    # PC 1: p1c1s, p1c2s, p1c3s. PC 2: ø
    s1 = yaml2json('1-device-with-components.snapshot')
    snapshot1, _ = user.post(json_encode(s1), res=Snapshot)
    # snapshot1 = snapshot_and_check(user,
    #                                s1,
    #                                action_types=(BenchmarkProcessor.t,
    #                                              RateComputer.t),
    #                                perform_second_snapshot=False)
    pc1_id = snapshot1['device']['id']
    pc1_dev = m.Device.query.filter_by(id=pc1_id).one()
    pc1_devicehub_id = pc1_dev.devicehub_id
    pc1, _ = user.get(res=m.Device, item=pc1_devicehub_id)
    update1_pc1 = pc1['updated']
    # Parent contains components
    assert (
        tuple(c['serialNumber'] for c in pc1['components'])
        == (
            'p1c1s',
            'p1c2s',
            'p1c3s',
        )
        == tuple(x.serial_number for x in pc1_dev.binding.device.components)
    )
    # Components contain parent
    assert all(c['parent'] == pc1_id for c in pc1['components'])
    # pc has three actions: Snapshot, BenchmarkProcessor and RateComputer
    assert len(pc1['actions']) == 2
    assert pc1['actions'][1]['type'] == Snapshot.t
    # p1c1s has Snapshot
    p1c1s_dev = m.Device.query.filter_by(id=pc1['components'][0]['id']).one()
    p1c1s, _ = user.get(res=m.Device, item=p1c1s_dev.devicehub_id)
    assert tuple(e['type'] for e in p1c1s['actions']) == ('Snapshot',)

    # We register a new device
    # It has the processor of the first one (p1c2s)
    # PC 1: p1c1s, p1c3s. PC 2: p2c1s, p1c2s
    # Actions PC1: Snapshot, Remove. PC2: Snapshot
    s2 = yaml2json('2-second-device-with-components-of-first.snapshot')
    # num_actions = 2 = Remove, Add
    snapshot2, _ = user.post(json_encode(s2), res=Snapshot)
    # snapshot2 = snapshot_and_check(user, s2, action_types=('Remove', 'RateComputer'),
    #                                perform_second_snapshot=False)
    pc2_id = snapshot2['device']['id']
    pc2_dev = m.Device.query.filter_by(id=pc2_id).one()
    pc2_devicehub_id = pc2_dev.devicehub_id
    pc1, _ = user.get(res=m.Device, item=pc1_devicehub_id)
    pc2, _ = user.get(res=m.Device, item=pc2_devicehub_id)
    # Check if the update_timestamp is updated
    # PC1
    assert tuple(c['serialNumber'] for c in pc1['components']) == (
        'p1c1s',
        'p1c2s',
        'p1c3s',
    )
    assert all(c['parent'] == pc1_id for c in pc1['components'])
    assert tuple(e['type'] for e in pc1['actions']) == (
        'BenchmarkProcessor',
        'Snapshot',
    )
    # PC2
    assert tuple(c['serialNumber'] for c in pc2['components']) == ('p2c1s', 'p1c2s')
    assert all(c['parent'] == pc2_id for c in pc2['components'])
    assert tuple(e['type'] for e in pc2['actions']) == ('Snapshot',)
    # p1c2s has two Snapshots, a Remove and an Add
    p1c2s_dev = m.Device.query.filter_by(id=pc2['components'][1]['id']).one()
    p1c2s, _ = user.get(res=m.Device, item=p1c2s_dev.devicehub_id)
    assert tuple(e['type'] for e in p1c2s['actions']) == ('Snapshot',)

    # We register the first device again, but removing motherboard
    # and moving processor from the second device to the first.
    # We have created 1 Remove (from PC2's processor back to PC1)
    # PC 0: p1c2s, p1c3s. PC 1: p2c1s
    s3 = yaml2json(
        '3-first-device-but-removing-motherboard-and-adding-processor-from-2.snapshot'
    )
    pc1, _ = user.get(res=m.Device, item=pc1_devicehub_id)
    pc2, _ = user.get(res=m.Device, item=pc2_devicehub_id)
    # Check if the update_timestamp is updated
    update2_pc2 = pc2['updated']
    update3_pc1 = pc1['updated']

    # PC1
    assert {c['serialNumber'] for c in pc1['components']} == {'p1c1s', 'p1c3s', 'p1c2s'}
    assert all(c['parent'] == pc1['id'] for c in pc1['components'])
    assert tuple(get_actions_info(pc1['actions'])) == (
        # id, type, components, snapshot
        ('BenchmarkProcessor', []),  # first BenchmarkProcessor
        ('Snapshot', ['p1c1s', 'p1c2s', 'p1c3s']),  # first Snapshot1
    )
    # PC2
    assert tuple(c['serialNumber'] for c in pc2['components']) == ('p2c1s', 'p1c2s')
    assert all(c['parent'] == pc2['id'] for c in pc2['components'])
    assert tuple(e['type'] for e in pc2['actions']) == ('Snapshot',)  # Second Snapshot
    # p1c2s has Snapshot, Remove and Add
    p1c2s_dev = m.Device.query.filter_by(id=pc1['components'][0]['id']).one()
    p1c2s, _ = user.get(res=m.Device, item=p1c2s_dev.devicehub_id)
    assert tuple(get_actions_info(p1c2s['actions'])) == (
        ('Snapshot', ['p1c1s', 'p1c2s', 'p1c3s']),  # First Snapshot to PC1
    )

    # We register the first device but without the processor,
    # adding a graphic card and adding a new component
    s4 = yaml2json(
        '4-first-device-but-removing-processor.snapshot-and-adding-graphic-card'
    )
    pc1, _ = user.get(res=m.Device, item=pc1_devicehub_id)
    pc2, _ = user.get(res=m.Device, item=pc2_devicehub_id)
    # Check if the update_timestamp is updated
    update3_pc2 = pc2['updated']
    update4_pc1 = pc1['updated']
    assert update3_pc2 == update2_pc2
    # PC 0: p1c3s, p1c4s. PC1: p2c1s
    assert {c['serialNumber'] for c in pc1['components']} == {'p1c1s', 'p1c2s', 'p1c3s'}
    assert all(c['parent'] == pc1['id'] for c in pc1['components'])
    # This last Action only
    # PC2
    # We haven't changed PC2
    assert tuple(c['serialNumber'] for c in pc2['components']) == ('p2c1s', 'p1c2s')
    assert all(c['parent'] == pc2['id'] for c in pc2['components'])


@pytest.mark.mvp
def test_snapshot_post_without_hid(user: UserClient):
    """Tests the post snapshot endpoint (validation, etc), data correctness,
    and relationship correctness with HID field generated with type - model - manufacturer - S/N.
    """
    snapshot_no_hid = file('basic.snapshot.nohid')
    response_snapshot, response_status = user.post(res=Snapshot, data=snapshot_no_hid)
    assert response_snapshot['software'] == 'Workbench'
    assert response_snapshot['version'] == '11.0b9'
    assert response_snapshot['uuid'] == '9a3e7485-fdd0-47ce-bcc7-65c55226b598'
    assert response_snapshot['elapsed'] == 4
    assert response_snapshot['author']['id'] == user.user['id']
    assert response_snapshot['severity'] == 'Info'
    assert response_status.status_code == 201


@pytest.mark.mvp
def test_snapshot_mismatch_id():
    """Tests uploading a device with an ID from another device."""
    # Note that this won't happen as in this new version
    # the ID is not used in the Snapshot process
    pass


@pytest.mark.mvp
def test_snapshot_tag_inner_tag_mismatch_between_tags_and_hid(
    user: UserClient, tag_id: str
):
    """Ensures one device cannot 'steal' the tag from another one."""
    pc1 = yaml2json('basic.snapshot')
    pc1['device']['tags'] = [{'type': 'Tag', 'id': tag_id}]
    user.post(json_encode(pc1), res=Snapshot)
    pc2 = yaml2json('1-device-with-components.snapshot')
    user.post(json_encode(pc2), res=Snapshot)  # PC2 uploads well
    pc2['device']['tags'] = [{'type': 'Tag', 'id': tag_id}]  # Set tag from pc1 to pc2
    user.post(json_encode(pc2), res=Snapshot, status=400)


@pytest.mark.mvp
def test_snapshot_different_properties_same_tags(user: UserClient, tag_id: str):
    """Tests a snapshot performed to device 1 with tag A and then to
    device 2 with tag B. Both don't have HID but are different type.
    Devicehub must fail the Snapshot.
    """
    # 1. Upload PC1 without hid but with tag
    pc1 = yaml2json('basic.snapshot')
    pc1['device']['tags'] = [{'type': 'Tag', 'id': tag_id}]
    del pc1['device']['serialNumber']
    user.post(json_encode(pc1), res=Snapshot)
    # 2. Upload PC2 without hid, a different characteristic than PC1, but with same tag
    pc2 = yaml2json('basic.snapshot')
    pc2['uuid'] = uuid4()
    pc2['device']['tags'] = pc1['device']['tags']
    # pc2 model is unknown but pc1 model is set = different property
    del pc2['device']['model']
    user.post(json_encode(pc2), res=Snapshot, status=201)


@pytest.mark.mvp
def test_snapshot_upload_twice_uuid_error(user: UserClient):
    pc1 = file('basic.snapshot')
    user.post(pc1, res=Snapshot)
    user.post(pc1, res=Snapshot, status=400)


@pytest.mark.mvp
def test_snapshot_component_containing_components(user: UserClient):
    """There is no reason for components to have components and when
    this happens it is always an error.

    This test avoids this until an appropriate use-case is presented.
    """
    s = yaml2json('basic.snapshot')
    s['device'] = {
        'type': 'Processor',
        'serialNumber': 'foo',
        'manufacturer': 'bar',
        'model': 'baz',
    }
    user.post(json_encode(s), res=Snapshot, status=ValidationError)


@pytest.mark.usefixtures(conftest.app_context.__name__)
@pytest.mark.mvp
def test_ram_remove(user: UserClient):
    """Tests a Snapshot
    We want check than all components is duplicate less hard disk, than this is removed.
    """
    s = yaml2json('erase-sectors.snapshot')
    s['device']['type'] = 'Server'
    snap1, _ = user.post(json_encode(s), res=Snapshot)

    s['uuid'] = '74caa7eb-2bad-4333-94f6-6f1b031d0774'
    s['device']['serialNumber'] = 'pc2s'
    snap2, _ = user.post(json_encode(s), res=Snapshot)

    dev1 = m.Device.query.filter_by(id=snap1['device']['id']).one()
    dev2 = m.Device.query.filter_by(id=snap2['device']['id']).one()
    assert len(dev1.components) == 2
    assert len(dev2.components) == 3
    ssd = [x for x in dev2.components if x.t == 'SolidStateDrive'][0]
    remove = [x for x in ssd.actions if x.t == 'Remove'][0]
    assert remove.t == 'Remove'


@pytest.mark.usefixtures(conftest.app_context.__name__)
@pytest.mark.mvp
def test_not_remove_ram_in_same_computer(user: UserClient):
    """Tests a Snapshot
    We want check than all components is not duplicate in a second snapshot of the same device.
    """
    s = yaml2json('erase-sectors.snapshot')
    s['device']['type'] = 'Server'
    snap1, _ = user.post(json_encode(s), res=Snapshot)

    s['uuid'] = '74caa7eb-2bad-4333-94f6-6f1b031d0774'
    s['components'].append(
        {
            "actions": [],
            "manufacturer": "Intel Corporation",
            "model": "NM10/ICH7 Family High Definition Audio Controller",
            "serialNumber": "mp2pc",
            "type": "SoundCard",
        }
    )
    dev1 = m.Device.query.filter_by(id=snap1['device']['id']).one()
    ram1 = [x.id for x in dev1.components if x.type == 'RamModule'][0]
    snap2, _ = user.post(json_encode(s), res=Snapshot)

    dev2 = m.Device.query.filter_by(id=snap2['device']['id']).one()
    ram2 = [x.id for x in dev2.components if x.type == 'RamModule'][0]
    assert ram1 != ram2
    assert len(dev1.components) == 4
    assert len(dev2.components) == 4
    assert dev1.id == dev2.id
    assert dev1.components == dev2.components


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_erase_privacy_standards_endtime_sort(user: UserClient):
    """Tests a Snapshot with EraseSectors and the resulting privacy
    properties.

    This tests ensures that only the last erasure is picked up, as
    erasures have always custom endTime value set.
    """
    s = yaml2json('erase-sectors.snapshot')
    assert s['components'][0]['actions'][0]['endTime'] == '2018-06-01T09:12:06+02:00'
    snapshot = snapshot_and_check(
        user,
        s,
        action_types=(
            EraseSectors.t,
            BenchmarkDataStorage.t,
            BenchmarkProcessor.t,
        ),
        perform_second_snapshot=False,
    )
    # Perform a new snapshot changing the erasure time, as if
    # it is a new erasure performed after.
    erase = next(e for e in snapshot['actions'] if e['type'] == EraseSectors.t)
    assert erase['endTime'] == '2018-06-01T07:12:06+00:00'
    s['uuid'] = uuid4()
    s['components'][0]['actions'][0]['endTime'] = '2018-06-01T07:14:00+00:00'
    snapshot = snapshot_and_check(
        user,
        s,
        action_types=(
            EraseSectors.t,
            BenchmarkDataStorage.t,
            BenchmarkProcessor.t,
        ),
        perform_second_snapshot=False,
    )

    # The actual test
    storage = next(e for e in snapshot['components'] if e['type'] == SolidStateDrive.t)
    db_storage = m.Device.query.filter_by(id=storage['id']).one()
    storage, _ = user.get(
        res=m.Device, item=db_storage.devicehub_id
    )  # Let's get storage actions too
    # order: endTime ascending
    #        erasure1/2 have an user defined time and others actions endTime = created
    (
        erasure1,
        erasure2,
        benchmark_hdd1,
        _snapshot1,
        benchmark_hdd2,
        _snapshot2,
    ) = storage['actions'][:8]
    assert erasure1['type'] == erasure2['type'] == 'EraseSectors'
    assert benchmark_hdd1['type'] == benchmark_hdd2['type'] == 'BenchmarkDataStorage'
    assert _snapshot1['type'] == _snapshot2['type'] == 'Snapshot'
    get_snapshot, _ = user.get(res=Action, item=_snapshot2['id'])
    assert get_snapshot['actions'][0]['endTime'] == '2018-06-01T07:14:00+00:00'
    assert snapshot == get_snapshot
    erasure, _ = user.get(res=Action, item=erasure1['id'])
    assert len(erasure['steps']) == 2
    assert erasure['steps'][0]['startTime'] == '2018-06-01T06:15:00+00:00'
    assert erasure['steps'][0]['endTime'] == '2018-06-01T07:16:00+00:00'
    assert erasure['steps'][1]['startTime'] == '2018-06-01T06:16:00+00:00'
    assert erasure['steps'][1]['endTime'] == '2018-06-01T07:17:00+00:00'
    assert erasure['device']['id'] == storage['id']
    step1, step2 = erasure['steps']
    assert step1['type'] == 'StepZero'
    assert step1['severity'] == 'Info'
    assert 'num' not in step1
    assert step2['type'] == 'StepRandom'
    assert step2['severity'] == 'Info'
    assert 'num' not in step2
    assert ['HMG_IS5'] == erasure['standards']
    assert storage['privacy']['type'] == 'EraseSectors'
    dev = m.Device.query.filter_by(id=snapshot['device']['id']).one()
    pc, _ = user.get(res=m.Device, item=dev.devicehub_id)
    # pc, _ = user.get(res=m.Device, item=snapshot['device']['devicehubID'])
    assert pc['privacy'] == [storage['privacy']]

    # Let's try a second erasure with an error
    s['uuid'] = uuid4()
    s['components'][0]['actions'][0]['severity'] = 'Error'
    snapshot, _ = user.post(json_encode(s), res=Snapshot)
    storage, _ = user.get(res=m.Device, item=db_storage.devicehub_id)
    assert storage['hid'] == 'solidstatedrive-c1mr-c1ml-c1s'
    assert dev.components[0].privacy.type == 'EraseSectors'
    assert storage['privacy']['type'] == 'EraseSectors'
    dev = m.Device.query.filter_by(id=snapshot['device']['id']).one()
    pc, _ = user.get(res=m.Device, item=dev.devicehub_id)
    assert pc['privacy'] == [storage['privacy']]


def test_test_data_storage(user: UserClient):
    """Tests a Snapshot with EraseSectors."""
    s = file('erase-sectors-2-hdd.snapshot')
    snapshot, _ = user.post(res=Snapshot, data=s)
    incidence_test = next(
        ev for ev in snapshot['actions'] if ev.get('reallocatedSectorCount', None) == 15
    )
    assert incidence_test['severity'] == 'Error'


def assert_similar_device(device1: dict, device2: dict):
    """Like :class:`ereuse_devicehub.resources.device.models.Device.
    is_similar()` but adapted for testing.
    """
    assert isinstance(device1, dict) and device1
    assert isinstance(device2, dict) and device2
    for key in 'serialNumber', 'model', 'manufacturer', 'type':
        if (device1.get(key, '') is not None) and (device2.get(key, '') is not None):
            assert device1.get(key, '').lower() == device2.get(key, '').lower()


def assert_similar_components(components1: List[dict], components2: List[dict]):
    """Asserts that the components in components1 are similar than
    the components in components2.
    """
    assert len(components1) == len(components2)
    key = itemgetter('serialNumber')
    components1.sort(key=key)
    components2.sort(key=key)
    for c1, c2 in zip(components1, components2):
        assert_similar_device(c1, c2)


def snapshot_and_check(
    user: UserClient,
    input_snapshot: dict,
    action_types: Tuple[str, ...] = tuple(),
    perform_second_snapshot=True,
) -> dict:
    """Performs a Snapshot and then checks if the result is ok:

    - There have been performed the types of actions and in the same
      order as described in the passed-in ``action_types``.
    - The inputted devices are similar to the resulted ones.
    - There is no Remove action after the first Add.
    - All input components are now inside the parent device.

    Optionally, it can perform a second Snapshot which should
    perform an exact result, except for the actions.

    :return: The last resulting snapshot.
    """
    snapshot, _ = user.post(res=Snapshot, data=json_encode(input_snapshot))
    assert all(e['type'] in action_types for e in snapshot['actions'])
    assert len(snapshot['actions']) == len(action_types)
    # Ensure there is no Remove action after the first Add
    found_add = False
    for action in snapshot['actions']:
        if action['type'] == 'Add':
            found_add = True
        if found_add:
            assert (
                action['type'] != 'Receive'
            ), 'All Remove actions must be before the Add ones'
    assert input_snapshot['device']
    assert_similar_device(input_snapshot['device'], snapshot['device'])
    if input_snapshot.get('components', None):
        assert_similar_components(input_snapshot['components'], snapshot['components'])
    assert all(
        c['parent'] == snapshot['device']['id'] for c in snapshot['components']
    ), 'Components must be in their parent'
    if perform_second_snapshot:
        if 'uuid' in input_snapshot:
            input_snapshot['uuid'] = uuid4()
        return snapshot_and_check(
            user, input_snapshot, action_types, perform_second_snapshot=False
        )
    else:
        return snapshot


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_erase_changing_hdd_between_pcs(user: UserClient):
    """Tests when we erase one device and next change the disk in other device we
    want see in the second device the disks erase."""
    s1 = file('erase-sectors-2-hdd.snapshot')
    s2 = file('erase-sectors-2-hdd.snapshot2')
    snapshot1, _ = user.post(res=Snapshot, data=s1)
    snapshot2, _ = user.post(res=Snapshot, data=s2)
    dev1 = m.Device.query.filter_by(id=snapshot1['device']['id']).one()
    dev2 = m.Device.query.filter_by(id=snapshot2['device']['id']).one()
    tag1 = Tag(id='dev1', device=dev1)
    tag2 = Tag(id='dev2', device=dev2)
    db.session.commit()

    assert dev2.components[2].parent == dev2
    assert dev2.components[2].actions[-1].device == dev2.components[2]
    doc1, response = user.get(
        res=documents.DocumentDef.t, item='erasures/{}'.format(dev1.id), accept=ANY
    )
    doc2, response = user.get(
        res=documents.DocumentDef.t, item='erasures/{}'.format(dev2.id), accept=ANY
    )
    assert 'dev1' in doc2
    assert 'dev2' in doc2


@pytest.mark.mvp
@pytest.mark.xfail(reason='Debug and rewrite it')
def test_pc_rating_rate_none(user: UserClient):
    """Tests a Snapshot with EraseSectors."""
    # TODO this snapshot have a benchmarkprocessor and a benchmarkprocessorsysbench
    s = file('desktop-9644w8n-lenovo-0169622.snapshot')
    snapshot, _ = user.post(res=Snapshot, data=s)


@pytest.mark.mvp
def test_pc_2(user: UserClient):
    s = file('laptop-hp_255_g3_notebook-hewlett-packard-cnd52270fw.snapshot')
    snapshot, _ = user.post(res=Snapshot, data=s)


@pytest.mark.mvp
def test_save_snapshot_in_file(app: Devicehub, user: UserClient):
    """This test check if works the function save_snapshot_in_file"""
    snapshot_no_hid = yaml2json('basic.snapshot.nohid')
    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'], 'errors')

    save_json(snapshot_no_hid, tmp_snapshots, user.user['email'])

    uuid = snapshot_no_hid['uuid']
    files = [x for x in os.listdir(path_dir_base) if uuid in x]

    snapshot = {'software': '', 'version': '', 'uuid': ''}
    if files:
        path_snapshot = os.path.join(path_dir_base, files[0])
        assert not "0001-01-01 00:00:00" in path_snapshot
        with open(path_snapshot) as file_snapshot:
            snapshot = json.loads(file_snapshot.read())

        shutil.rmtree(tmp_snapshots)

    assert snapshot['software'] == snapshot_no_hid['software']
    assert snapshot['version'] == snapshot_no_hid['version']
    assert snapshot['uuid'] == uuid


@pytest.mark.mvp
def test_action_no_snapshot_without_save_file(app: Devicehub, user: UserClient):
    """This test check if the function save_snapshot_in_file not work when we
    send one other action different to snapshot
    """
    s = file('laptop-hp_255_g3_notebook-hewlett-packard-cnd52270fw.snapshot')
    snapshot, _ = user.post(res=Snapshot, data=s)

    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'])

    shutil.rmtree(tmp_snapshots)

    action = {'type': Ready.t, 'devices': [snapshot['device']['id']]}
    action, _ = user.post(action, res=Action)

    assert os.path.exists(tmp_snapshots) == False


@pytest.mark.mvp
def test_save_snapshot_with_debug(app: Devicehub, user: UserClient):
    """This test check if works the function save_snapshot_in_file"""
    snapshot_file = yaml2json('basic.snapshot.with_debug')
    debug = snapshot_file['debug']
    user.post(res=Snapshot, data=json_encode(snapshot_file))

    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'])

    uuid = snapshot_file['uuid']
    files = [x for x in os.listdir(path_dir_base) if uuid in x]

    snapshot = {'debug': ''}
    if files:
        path_snapshot = os.path.join(path_dir_base, files[0])
        with open(path_snapshot) as file_snapshot:
            snapshot = json.loads(file_snapshot.read())

        shutil.rmtree(tmp_snapshots)

    assert snapshot['debug'] == debug


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_backup_snapshot_with_errors(app: Devicehub, user: UserClient):
    """This test check if the file snapshot is create when some snapshot is wrong"""
    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'], 'errors')
    snapshot_no_hid = yaml2json('basic.snapshot.badly_formed')
    uuid = snapshot_no_hid['uuid']

    snapshot = {'software': '', 'version': '', 'uuid': ''}
    with pytest.raises(KeyError):
        response = user.post(res=Snapshot, data=json_encode(snapshot_no_hid))

    errors = SnapshotsLog.query.filter().all()
    snap_log = errors[1]
    assert snap_log.description == "'BenchmarkProcessorr'"
    assert errors[0].description == 'There is not uuid'
    assert snap_log.version == "11.0b9"
    assert str(snap_log.snapshot_uuid) == '9a3e7485-fdd0-47ce-bcc7-65c55226b598'
    assert str(errors[0].snapshot_uuid) == '9a3e7485-fdd0-47ce-bcc7-65c55226b598'
    assert len(errors) == 2

    files = [x for x in os.listdir(path_dir_base) if uuid in x]
    if files:
        path_snapshot = os.path.join(path_dir_base, files[0])
        with open(path_snapshot) as file_snapshot:
            snapshot = json.loads(file_snapshot.read())

        shutil.rmtree(tmp_snapshots)

    assert snapshot['software'] == snapshot_no_hid['software']
    assert snapshot['version'] == snapshot_no_hid['version']
    assert snapshot['uuid'] == uuid


@pytest.mark.mvp
def test_snapshot_failed_missing_cpu_benchmark(app: Devicehub, user: UserClient):
    """This test check if the file snapshot is create when some snapshot is wrong"""
    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'], 'errors')
    snapshot_error = yaml2json('failed.snapshot.500.missing-cpu-benchmark')
    uuid = snapshot_error['uuid']

    snapshot = {'software': '', 'version': '', 'uuid': ''}
    with pytest.raises(TypeError):
        user.post(res=Snapshot, data=json_encode(snapshot_error))

    files = [x for x in os.listdir(path_dir_base) if uuid in x]
    if files:
        path_snapshot = os.path.join(path_dir_base, files[0])
        with open(path_snapshot) as file_snapshot:
            snapshot = json.loads(file_snapshot.read())

        shutil.rmtree(tmp_snapshots)

    assert snapshot['software'] == snapshot_error['software']
    assert snapshot['version'] == snapshot_error['version']
    assert snapshot['uuid'] == uuid


@pytest.mark.mvp
def test_snapshot_failed_missing_hdd_benchmark(app: Devicehub, user: UserClient):
    """This test check if the file snapshot is create when some snapshot is wrong"""
    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'], 'errors')
    snapshot_error = yaml2json('failed.snapshot.500.missing-hdd-benchmark')
    uuid = snapshot_error['uuid']

    snapshot = {'software': '', 'version': '', 'uuid': ''}
    with pytest.raises(TypeError):
        user.post(res=Snapshot, data=json_encode(snapshot_error))

    files = [x for x in os.listdir(path_dir_base) if uuid in x]
    if files:
        path_snapshot = os.path.join(path_dir_base, files[0])
        with open(path_snapshot) as file_snapshot:
            snapshot = json.loads(file_snapshot.read())

        shutil.rmtree(tmp_snapshots)

    assert snapshot['software'] == snapshot_error['software']
    assert snapshot['version'] == snapshot_error['version']
    assert snapshot['uuid'] == uuid


@pytest.mark.mvp
def test_snapshot_not_failed_null_chassis(app: Devicehub, user: UserClient):
    """This test check if the file snapshot is create when some snapshot is wrong"""
    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'], 'errors')
    snapshot_error = yaml2json('desktop-9644w8n-lenovo-0169622.snapshot')
    snapshot_error['device']['chassis'] = None
    uuid = snapshot_error['uuid']

    snapshot, res = user.post(res=Snapshot, data=json_encode(snapshot_error))

    shutil.rmtree(tmp_snapshots)

    assert snapshot['software'] == snapshot_error['software']
    assert snapshot['version'] == snapshot_error['version']
    assert snapshot['uuid'] == uuid


@pytest.mark.mvp
def test_snapshot_failed_missing_chassis(app: Devicehub, user: UserClient):
    """This test check if the file snapshot is create when some snapshot is wrong"""
    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'], 'errors')
    snapshot_error = yaml2json('failed.snapshot.422.missing-chassis')
    uuid = snapshot_error['uuid']

    snapshot = {'software': '', 'version': '', 'uuid': ''}
    with pytest.raises(TypeError):
        user.post(res=Snapshot, data=json_encode(snapshot_error))

    files = [x for x in os.listdir(path_dir_base) if uuid in x]
    if files:
        path_snapshot = os.path.join(path_dir_base, files[0])
        with open(path_snapshot) as file_snapshot:
            snapshot = json.loads(file_snapshot.read())

        shutil.rmtree(tmp_snapshots)

    assert snapshot['software'] == snapshot_error['software']
    assert snapshot['version'] == snapshot_error['version']
    assert snapshot['uuid'] == uuid


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_failed_end_time_bug(app: Devicehub, user: UserClient):
    """This test check if the end_time = 0001-01-01 00:00:00+00:00
    and then we get a /devices, this create a crash
    """
    snapshot_file = file('asus-end_time_bug88.snapshot')
    snapshot, _ = user.post(res=Snapshot, data=snapshot_file)
    dev = m.Device.query.filter_by(id=snapshot['device']['id']).one()
    device, _ = user.get(res=m.Device, item=dev.devicehub_id)
    end_times = [x['endTime'] for x in device['actions']]

    assert '1970-01-02T00:00:00+00:00' in end_times
    assert '0001-01-01T00:00:00+00:00' not in end_times

    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_not_failed_end_time_bug(app: Devicehub, user: UserClient):
    """This test check if the end_time != 0001-01-01 00:00:00+00:00
    and then we get a /devices, this create a crash
    """
    snapshot_file = yaml2json('asus-end_time_bug88.snapshot')
    snapshot_file['endTime'] = '2001-01-01 00:00:00+00:00'
    snapshot, _ = user.post(res=Snapshot, data=json_encode(snapshot_file))
    db_dev = Device.query.filter_by(id=snapshot['device']['id']).one()
    device, _ = user.get(res=m.Device, item=db_dev.devicehub_id)
    end_times = [x['endTime'] for x in device['actions']]

    assert not '1970-01-02T00:00:00+00:00' in end_times
    assert not '0001-01-01T00:00:00+00:00' in end_times
    assert '2001-01-01T00:00:00+00:00' in end_times

    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
def test_snapshot_bug_smallint_hdd(app: Devicehub, user: UserClient):
    """This test check if the end_time != 0001-01-01 00:00:00+00:00
    and then we get a /devices, this create a crash
    """
    snapshot_file = file('asus-eee-1000h.snapshot.bug1857')
    snapshot, _ = user.post(res=Snapshot, data=snapshot_file)

    act = [act for act in snapshot['actions'] if act['type'] == 'TestDataStorage'][0]
    assert act['currentPendingSectorCount'] == 473302660
    assert act['offlineUncorrectable'] == 182042944

    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
def test_snapshot_mobil(app: Devicehub, user: UserClient):
    """This test check if the end_time != 0001-01-01 00:00:00+00:00
    and then we get a /devices, this create a crash
    """
    snapshot_file = file('mobil')
    snapshot, _ = user.post(res=Snapshot, data=snapshot_file)
    device, _ = user.get(res=m.Device, item=snapshot['device']['devicehubID'])

    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
def test_bug_141(user: UserClient):
    """This test check one bug that create a problem when try to up one snapshot
    with a big number in the parameter command_timeout of the DataStorage

    """
    dev = file('2021-5-4-13-41_time_out_test_datastorage')
    user.post(dev, res=Snapshot)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_wb_lite(user: UserClient):
    """This test check the minimum validation of json that come from snapshot"""

    snapshot = file_json(
        "2022-03-31_17h18m51s_ZQMPKKX51K67R68VO2X9RNZL08JPL_snapshot.json"
    )
    body, res = user.post(snapshot, uri="/api/inventory/")

    dev = m.Device.query.filter_by(devicehub_id=body['dhid']).one()
    dev = dev.placeholder.binding
    ssd = [x for x in dev.components if x.type == 'SolidStateDrive'][0]

    assert dev.manufacturer == 'lenovo'
    assert dev.dhid in body['public_url']
    assert ssd.serial_number == 's35anx0j401001'
    assert res.status == '201 CREATED'
    chid = '7619bf5dfa630c8bd6d431c56777f6334d5c1e2e55d90c0dc4d1e99f80f031c1'
    assert dev.chid == chid

    assert dev.actions[0].power_on_hours == 6032
    errors = SnapshotsLog.query.filter().all()
    assert len(errors) == 1
    assert errors[0].description == 'Ok'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_wb_lite_qemu(user: UserClient):
    """This test check the minimum validation of json that come from snapshot"""

    snapshot = file_json("qemu-cc9927a9-55ad-4937-b36b-7185147d9fa9.json")
    body, res = user.post(snapshot, uri="/api/inventory/")

    assert res.status == '201 CREATED'

    dev = m.Device.query.filter_by(devicehub_id=body['dhid']).one()
    dev = dev.placeholder.binding
    assert dev.dhid in body['public_url']
    assert dev.manufacturer == 'qemu'
    assert dev.model == 'standard'
    assert dev.serial_number is None
    assert dev.hid == 'computer-qemu-standard-'
    assert dev.actions[0].power_on_hours == 1
    assert dev.components[-1].size == 40960
    assert dev.components[-1].serial_number == 'qm00001'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_wb_lite_old_snapshots(user: UserClient):
    """This test check the minimum validation of json that come from snapshot"""
    wb_dir = Path(__file__).parent.joinpath('files/wb_lite/')
    for f in os.listdir(wb_dir):
        file_name = "wb_lite/{}".format(f)
        snapshot_11 = file_json(file_name)
        if not snapshot_11.get('debug'):
            continue
        lshw = snapshot_11['debug']['lshw']
        hwinfo = snapshot_11['debug']['hwinfo']
        snapshot_lite = {
            'timestamp': snapshot_11['endTime'],
            'type': 'Snapshot',
            'uuid': str(uuid.uuid4()),
            'sid': 'MLKO1',
            'software': 'Workbench',
            'version': '2022.03.00',
            "schema_api": "1.0.0",
            'data': {
                'lshw': lshw,
                'hwinfo': hwinfo,
                'smart': [],
                'dmidecode': '',
                'lspci': '',
            },
        }

        body11, res = user.post(snapshot_11, res=Snapshot)
        bodyLite, res = user.post(snapshot_lite, uri="/api/inventory/")
        dev = m.Device.query.filter_by(devicehub_id=bodyLite['dhid']).one()
        components11 = []
        componentsLite = []
        for c in body11.get('components', []):
            if c['type'] in ["HardDrive", "SolidStateDrive"]:
                continue
            components11.append({c.get('model'), c['type'], c.get('manufacturer')})
        for c in dev.components:
            componentsLite.append({c.model, c.type, c.manufacturer})

        try:
            assert body11['device'].get('hid') == dev.hid
            if body11['device'].get('hid'):
                assert body11['device']['id'] != dev.id
            assert body11['device'].get('serialNumber') == dev.serial_number
            assert body11['device'].get('model') == dev.model
            assert body11['device'].get('manufacturer') == dev.manufacturer

            # wbLite can find more components than wb11
            assert len(components11) <= len(componentsLite)
            for c in components11:
                assert c in componentsLite
        except Exception as err:
            raise err


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_lite_error_400(user: UserClient):
    """This test check the minimum validation of json that come from snapshot"""
    snapshot_11 = file_json('snapshotErrors.json')
    lshw = snapshot_11['debug']['lshw']
    snapshot_lite = {
        'timestamp': snapshot_11['endTime'],
        'type': 'Snapshot',
        'uuid': str(uuid.uuid4()),
        'sid': 'MLKO1',
        'software': 'Workbench',
        'version': '2022.03.00',
        "schema_api": "1.0.0",
    }

    user.post(snapshot_lite, uri="/api/inventory/", status=400)

    for k in ['lshw', 'hwinfo', 'smart', 'dmidecode', 'lspci']:
        data = {
            'lshw': lshw,
            'hwinfo': '',
            'smart': [],
            'dmidecode': '',
            'lspci': '',
        }
        data.pop(k)
        snapshot_lite['data'] = data
        user.post(snapshot_lite, uri="/api/inventory/", status=400)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_lite_error_422(user: UserClient):
    """This test check the minimum validation of json that come from snapshot"""
    snapshot_11 = file_json('snapshotErrors.json')
    snapshot_lite = {
        'timestamp': snapshot_11['endTime'],
        'type': 'Snapshot',
        'uuid': str(uuid.uuid4()),
        'sid': 'MLKO1',
        'software': 'Workbench',
        'version': '2022.03.00',
        "schema_api": "1.0.0",
        'data': {
            'lshw': {},
            'hwinfo': '',
            'smart': [],
            'dmidecode': '',
            'lspci': '',
        },
    }

    user.post(snapshot_lite, uri="/api/inventory/", status=422)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_lite_minimum(user: UserClient):
    """This test check the minimum validation of json that come from snapshot"""
    snapshot_11 = file_json('snapshotErrors.json')
    lshw = snapshot_11['debug']['lshw']
    snapshot_lite = {
        'timestamp': snapshot_11['endTime'],
        'type': 'Snapshot',
        'uuid': str(uuid.uuid4()),
        'sid': 'MLKO1',
        'software': 'Workbench',
        'version': '2022.03.00',
        "schema_api": "1.0.0",
        'data': {
            'lshw': lshw,
            'hwinfo': '',
            'smart': [],
            'dmidecode': '',
            'lspci': '',
        },
    }
    bodyLite, res = user.post(snapshot_lite, uri="/api/inventory/")
    dev = m.Device.query.filter_by(devicehub_id=bodyLite['dhid']).one()
    assert dev.dhid in bodyLite['public_url']
    assert res.status_code == 201


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_lite_error_in_components(user: UserClient):
    """This test check the minimum validation of json that come from snapshot"""
    snapshot_11 = file_json('snapshotErrorsComponents.json')
    lshw = snapshot_11['debug']['lshw']
    snapshot_lite = {
        'timestamp': snapshot_11['endTime'],
        'type': 'Snapshot',
        'uuid': str(uuid.uuid4()),
        'sid': 'MLKO1',
        'software': 'Workbench',
        'version': '2022.03.00',
        "schema_api": "1.0.0",
        'data': {
            'lshw': lshw,
            'hwinfo': '',
            'smart': [],
            'dmidecode': '',
            'lspci': '',
        },
    }
    bodyLite, res = user.post(snapshot_lite, uri="/api/inventory/")
    assert res.status_code == 201

    dev = m.Device.query.filter_by(devicehub_id=bodyLite['dhid']).one()
    assert dev.dhid in bodyLite['public_url']
    assert 'Motherboard' not in [x.type for x in dev.components]
    error = SnapshotsLog.query.all()
    assert 'StopIteration' in error[0].description


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_lite_error_403(client: Client):
    """This test check the minimum validation of json that come from snapshot"""
    snapshot_11 = file_json('snapshotErrors.json')
    lshw = snapshot_11['debug']['lshw']
    snapshot_lite = {
        'timestamp': snapshot_11['endTime'],
        'type': 'Snapshot',
        'uuid': str(uuid.uuid4()),
        'sid': 'MLKO1',
        'software': 'Workbench',
        'version': '2022.03.00',
        "schema_api": "1.0.0",
        'data': {
            'lshw': lshw,
            'hwinfo': '',
            'smart': [],
            'dmidecode': '',
            'lspci': '',
        },
    }
    client.post(snapshot_lite, uri="/api/inventory/", status=401)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_errors(user: UserClient):
    """This test check the minimum validation of json that come from snapshot"""
    snapshot_11 = file_json('snapshotErrors.json')
    lshw = snapshot_11['debug']['lshw']
    hwinfo = snapshot_11['debug']['hwinfo']
    snapshot_lite = {
        'timestamp': snapshot_11['endTime'],
        'type': 'Snapshot',
        'uuid': str(uuid.uuid4()),
        'sid': 'MLKO1',
        'software': 'Workbench',
        'version': '2022.03.00',
        "schema_api": "1.0.0",
        'data': {
            'lshw': lshw,
            'hwinfo': hwinfo,
            'smart': [],
            'dmidecode': '',
            'lspci': '',
        },
    }

    assert SnapshotsLog.query.all() == []
    body11, res = user.post(snapshot_11, res=Snapshot)
    assert len(SnapshotsLog.query.all()) == 1
    bodyLite, res = user.post(snapshot_lite, uri="/api/inventory/")
    dev = m.Device.query.filter_by(devicehub_id=bodyLite['dhid']).one()
    dev = dev.placeholder.binding
    assert len(SnapshotsLog.query.all()) == 4

    assert body11['device'].get('hid') == dev.hid
    assert body11['device']['id'] == dev.id
    assert body11['device'].get('serialNumber') == dev.serial_number
    assert body11['device'].get('model') == dev.model
    assert body11['device'].get('manufacturer') == dev.manufacturer
    components11 = []
    componentsLite = []
    for c in body11['components']:
        if c['type'] == "HardDrive":
            continue
        components11.append({c['model'], c['type'], c['manufacturer']})
    for c in dev.components:
        componentsLite.append({c.model, c.type, c.manufacturer})

    assert len(components11) == len(componentsLite)
    for c in components11:
        assert c in componentsLite


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_errors_timestamp(user: UserClient):
    """This test check the minimum validation of json that come from snapshot"""
    snapshot_lite = file_json('snapshot-error-timestamp.json')
    user.post(snapshot_lite, uri="/api/inventory/", status=422)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_errors_no_serial_number(user: UserClient):
    """This test check the minimum validation of json that come from snapshot"""
    snapshot_lite = file_json('desktop-amd-bug-no-sn.json')

    bodyLite, res = user.post(snapshot_lite, uri="/api/inventory/")
    assert res.status_code == 201
    logs = SnapshotsLog.query.all()
    assert len(logs) == 1
    assert logs[0].description == 'Ok'
    dev = m.Device.query.filter_by(devicehub_id=bodyLite['dhid']).one()
    dev = dev.placeholder.binding
    assert not dev.model
    assert not dev.manufacturer
    assert not dev.serial_number
    assert dev.type == "Desktop"
    for c in dev.components:
        if not c.type == "HardDrive":
            continue
        assert c.serial_number == 'vd051gtf024b4l'
        assert c.model == "hdt722520dlat80"
        assert not c.manufacturer
        test = c.actions[-1]
        assert test.power_on_hours == 19819


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_check_tests_lite(user: UserClient):
    """This test check the minimum validation of json that come from snapshot"""
    snapshot_lite = file_json(
        'test_lite/2022-4-13-19-5_user@dhub.com_b27dbf43-b88a-4505-ae27-10de5a95919e.json'
    )

    bodyLite, res = user.post(snapshot_lite, uri="/api/inventory/")
    assert res.status_code == 201
    assert SnapshotsLog.query.count() == 1
    m.Device.query.filter_by(devicehub_id=bodyLite['dhid']).one()


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_placeholder(user: UserClient):
    """This check the structure of one placeholder generated automatically by a snapshot"""
    snapshot_lite = file_json(
        'test_lite/2022-4-13-19-5_user@dhub.com_b27dbf43-b88a-4505-ae27-10de5a95919e.json'
    )

    bodyLite, res = user.post(snapshot_lite, uri="/api/inventory/")
    assert res.status_code == 201
    dev = m.Device.query.filter_by(devicehub_id=bodyLite['dhid']).one()
    dev = dev.placeholder.binding
    assert dev.placeholder is None
    assert dev.binding.phid == '12'
    assert len(dev.binding.device.components) == 11
    assert len(dev.components) == 11
    assert dev.binding.device.placeholder == dev.binding
    assert dev.components != dev.binding.device.components
    assert dev.binding.device.actions == []


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_placeholder_actions(user: UserClient):
    """This test the actions of a placeholder of one snapshot"""
    s = yaml2json('erase-sectors.snapshot')
    snap1, _ = user.post(s, res=Snapshot)

    dev = m.Device.query.filter_by(id=snap1['device']['id']).one()
    assert dev.placeholder is None
    assert dev.binding.phid == '4'
    assert len(dev.binding.device.components) == 3
    assert len(dev.components) == 3
    assert dev.binding.device.placeholder == dev.binding
    assert dev.components != dev.binding.device.components
    assert dev.binding.device.actions == []
    assert len(dev.components[0].actions) == 3
    assert len(dev.binding.device.components[0].actions) == 0


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_system_uuid_motherboard(user: UserClient):
    """This test the actions of a placeholder of one snapshot"""
    s = yaml2json('real-eee-1001pxd.snapshot.12')
    snap1, _ = user.post(s, res=Snapshot)

    for c in s['components']:
        if c['type'] == 'Motherboard':
            c['serialNumber'] = 'ABee0123456720'

    s['uuid'] = str(uuid.uuid4())
    snap2, _ = user.post(s, res=Snapshot, status=422)
    txt = "We have detected that a there is a device in your inventory"
    assert txt in snap2['message'][0]


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_bug_4028_components(user: UserClient):
    """Tests when we have one computer and then we change the disk, then
    the new disk need to have placeholder too."""
    s = yaml2json('real-eee-1001pxd.snapshot.12')
    snap1, _ = user.post(s, res=Snapshot)
    dev1 = m.Device.query.filter_by(id=snap1['device']['id']).one()
    assert m.Placeholder.query.count() * 2 == m.Device.query.count()
    components1 = [c for c in dev1.components]
    for c in s['components']:
        if c['type'] == 'HardDrive':
            c['serialNumber'] = 'E2024242CV86MF'

    s['uuid'] = str(uuid4())
    snap2, _ = user.post(s, res=Snapshot)
    dev2 = m.Device.query.filter_by(id=snap2['device']['id']).one()
    components2 = [c for c in dev2.components]

    assert '' not in [c.phid() for c in components1]
    assert '' not in [c.phid() for c in components2]
    assert len(components1) == len(components2)
    assert m.Placeholder.query.count() == 19
    assert m.Placeholder.query.count() * 2 == m.Device.query.count()
    for c in m.Placeholder.query.filter():
        assert c.binding
        assert c.device

    for c in m.Device.query.filter():
        assert c.binding or c.placeholder


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_settings_version(user: UserClient):
    """Tests when we have one computer and then we change the disk, then
    the new disk need to have placeholder too."""
    s = file_json("2022-03-31_17h18m51s_ZQMPKKX51K67R68VO2X9RNZL08JPL_snapshot.json")
    body, res = user.post(s, uri="/api/inventory/")
    assert m.Computer.query.first().dhid == body['dhid']
    snapshot = Snapshot.query.first()
    log = SnapshotsLog.query.first()

    assert log.get_version() == "14.0 (BM)"
    assert snapshot.settings_version == "Basic Metadata"
