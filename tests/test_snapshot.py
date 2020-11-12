import os
import json
import shutil
import pytest

from datetime import datetime, timedelta, timezone
from requests.exceptions import HTTPError
from operator import itemgetter
from typing import List, Tuple
from uuid import uuid4

from boltons import urlutils
from teal.db import UniqueViolation, DBError
from teal.marshmallow import ValidationError

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.action.models import Action, BenchmarkDataStorage, \
    BenchmarkProcessor, EraseSectors, RateComputer, Snapshot, SnapshotRequest, VisualTest, \
    EreusePrice
from ereuse_devicehub.resources.device import models as m
from ereuse_devicehub.resources.device.exceptions import NeedsId
from ereuse_devicehub.resources.device.models import SolidStateDrive
from ereuse_devicehub.resources.device.sync import MismatchBetweenProperties, \
    MismatchBetweenTagsAndHid
from ereuse_devicehub.resources.enums import ComputerChassis, SnapshotSoftware
from ereuse_devicehub.resources.tag import Tag
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.action.views import save_json
from tests.conftest import file


@pytest.mark.mvp
@pytest.mark.usefixtures('auth_app_context')
def test_snapshot_model():
    """Tests creating a Snapshot with its relationships ensuring correct
    DB mapping.
    """
    device = m.Desktop(serial_number='a1', chassis=ComputerChassis.Tower)
    # noinspection PyArgumentList
    snapshot = Snapshot(uuid=uuid4(),
                        end_time=datetime.now(timezone.utc),
                        version='1.0',
                        software=SnapshotSoftware.DesktopApp,
                        elapsed=timedelta(seconds=25))
    snapshot.device = device
    snapshot.request = SnapshotRequest(request={'foo': 'bar'})
    db.session.add(snapshot)
    db.session.commit()
    device = m.Desktop.query.one()  # type: m.Desktop
    e1 = device.actions[0]
    assert isinstance(e1, Snapshot), 'Creation order must be preserved: 1. snapshot, 2. WR'
    db.session.delete(device)
    db.session.commit()
    assert Snapshot.query.one_or_none() is None
    assert SnapshotRequest.query.one_or_none() is None
    assert User.query.one() is not None
    assert m.Desktop.query.one_or_none() is None
    assert m.Device.query.one_or_none() is None
    # Check properties
    assert device.url == urlutils.URL('http://localhost/devices/1')


@pytest.mark.mvp
def test_snapshot_schema(app: Devicehub):
    with app.app_context():
        s = file('basic.snapshot')
        app.resources['Snapshot'].schema.load(s)


@pytest.mark.mvp
def test_snapshot_post(user: UserClient):
    """Tests the post snapshot endpoint (validation, etc), data correctness,
    and relationship correctness.
    """
    snapshot = snapshot_and_check(user, file('basic.snapshot'),
                                  action_types=(
                                      BenchmarkProcessor.t,
                                      VisualTest.t,
                                      RateComputer.t
                                  ),
                                  perform_second_snapshot=False)
    assert snapshot['software'] == 'Workbench'
    assert snapshot['version'] == '11.0'
    assert snapshot['uuid'] == 'f5efd26e-8754-46bc-87bf-fbccc39d60d9'
    assert snapshot['elapsed'] == 4
    assert snapshot['author']['id'] == user.user['id']
    assert 'actions' not in snapshot['device']
    assert 'author' not in snapshot['device']
    device, _ = user.get(res=m.Device, item=snapshot['device']['id'])
    key = itemgetter('serialNumber')
    snapshot['components'].sort(key=key)
    device['components'].sort(key=key)
    assert snapshot['components'] == device['components']

    assert {c['type'] for c in snapshot['components']} == {m.GraphicCard.t, m.RamModule.t,
                                                           m.Processor.t}
    rate = next(e for e in snapshot['actions'] if e['type'] == RateComputer.t)
    rate, _ = user.get(res=Action, item=rate['id'])
    assert rate['device']['id'] == snapshot['device']['id']
    rate['components'].sort(key=key)
    assert rate['components'] == snapshot['components']
    assert rate['snapshot']['id'] == snapshot['id']


@pytest.mark.mvp
def test_snapshot_update_timefield_updated(user: UserClient):
    """
    Tests for check if one computer have the time mark updated when one component of it is updated
    """
    computer1 = file('1-device-with-components.snapshot')
    snapshot = snapshot_and_check(user,
                                  computer1,
                                  action_types=(BenchmarkProcessor.t,
                                                RateComputer.t),
                                  perform_second_snapshot=False)
    computer2 = file('2-second-device-with-components-of-first.snapshot')
    snapshot_and_check(user, computer2, action_types=('Remove', 'RateComputer'),
                       perform_second_snapshot=False)
    pc1_id = snapshot['device']['id']
    pc1, _ = user.get(res=m.Device, item=pc1_id)
    assert pc1['updated'] != snapshot['device']['updated']


@pytest.mark.mvp
def test_snapshot_component_add_remove(user: UserClient):
    """Tests adding and removing components and some don't generate HID.
    All computers generate HID.
    """

    def get_actions_info(actions: List[dict]) -> tuple:
        return tuple(
            (
                e['type'],
                [c['serialNumber'] for c in e['components']]
            )
            for e in user.get_many(res=Action, resources=actions, key='id')
        )

    # We add the first device (2 times). The distribution of components
    # (represented with their S/N) should be:
    # PC 1: p1c1s, p1c2s, p1c3s. PC 2: ø
    s1 = file('1-device-with-components.snapshot')
    snapshot1 = snapshot_and_check(user,
                                   s1,
                                   action_types=(BenchmarkProcessor.t,
                                                 RateComputer.t),
                                   perform_second_snapshot=False)
    pc1_id = snapshot1['device']['id']
    pc1, _ = user.get(res=m.Device, item=pc1_id)
    update1_pc1 = pc1['updated']
    # Parent contains components
    assert tuple(c['serialNumber'] for c in pc1['components']) == ('p1c1s', 'p1c2s', 'p1c3s')
    # Components contain parent
    assert all(c['parent'] == pc1_id for c in pc1['components'])
    # pc has three actions: Snapshot, BenchmarkProcessor and RateComputer
    assert len(pc1['actions']) == 3
    assert pc1['actions'][1]['type'] == Snapshot.t
    # p1c1s has Snapshot
    p1c1s, _ = user.get(res=m.Device, item=pc1['components'][0]['id'])
    assert tuple(e['type'] for e in p1c1s['actions']) == ('Snapshot', 'RateComputer')

    # We register a new device
    # It has the processor of the first one (p1c2s)
    # PC 1: p1c1s, p1c3s. PC 2: p2c1s, p1c2s
    # Actions PC1: Snapshot, Remove. PC2: Snapshot
    s2 = file('2-second-device-with-components-of-first.snapshot')
    # num_actions = 2 = Remove, Add
    snapshot2 = snapshot_and_check(user, s2, action_types=('Remove', 'RateComputer'),
                                   perform_second_snapshot=False)
    pc2_id = snapshot2['device']['id']
    pc1, _ = user.get(res=m.Device, item=pc1_id)
    pc2, _ = user.get(res=m.Device, item=pc2_id)
    # Check if the update_timestamp is updated
    update1_pc2 = pc2['updated']
    update2_pc1 = pc1['updated']
    assert update1_pc1 != update2_pc1
    # PC1
    assert tuple(c['serialNumber'] for c in pc1['components']) == ('p1c1s', 'p1c3s')
    assert all(c['parent'] == pc1_id for c in pc1['components'])
    assert tuple(e['type'] for e in pc1['actions']) == ('BenchmarkProcessor', 'Snapshot', 'RateComputer', 'Remove')
    # PC2
    assert tuple(c['serialNumber'] for c in pc2['components']) == ('p1c2s', 'p2c1s')
    assert all(c['parent'] == pc2_id for c in pc2['components'])
    assert tuple(e['type'] for e in pc2['actions']) == ('Snapshot', 'RateComputer')
    # p1c2s has two Snapshots, a Remove and an Add
    p1c2s, _ = user.get(res=m.Device, item=pc2['components'][0]['id'])
    assert tuple(e['type'] for e in p1c2s['actions']) == (
        'BenchmarkProcessor', 'Snapshot', 'RateComputer', 'Snapshot', 'Remove', 'RateComputer'
    )

    # We register the first device again, but removing motherboard
    # and moving processor from the second device to the first.
    # We have created 1 Remove (from PC2's processor back to PC1)
    # PC 0: p1c2s, p1c3s. PC 1: p2c1s
    s3 = file('3-first-device-but-removing-motherboard-and-adding-processor-from-2.snapshot')
    snapshot_and_check(user, s3, ('Remove', 'RateComputer'), perform_second_snapshot=False)
    pc1, _ = user.get(res=m.Device, item=pc1_id)
    pc2, _ = user.get(res=m.Device, item=pc2_id)
    # Check if the update_timestamp is updated
    update2_pc2 = pc2['updated']
    update3_pc1 = pc1['updated']
    assert not update3_pc1 in [update1_pc1, update2_pc1]
    assert update1_pc2 != update2_pc2

    # PC1
    assert {c['serialNumber'] for c in pc1['components']} == {'p1c2s', 'p1c3s'}
    assert all(c['parent'] == pc1_id for c in pc1['components'])
    assert tuple(get_actions_info(pc1['actions'])) == (
        # id, type, components, snapshot
        ('BenchmarkProcessor', []),  # first BenchmarkProcessor
        ('Snapshot', ['p1c1s', 'p1c2s', 'p1c3s']),  # first Snapshot1
        ('RateComputer', ['p1c1s', 'p1c2s', 'p1c3s']),
        ('Remove', ['p1c2s']),  # Remove Processor in Snapshot2
        ('Snapshot', ['p1c2s', 'p1c3s']),  # This Snapshot3
        ('RateComputer', ['p1c2s', 'p1c3s'])
    )
    # PC2
    assert tuple(c['serialNumber'] for c in pc2['components']) == ('p2c1s',)
    assert all(c['parent'] == pc2_id for c in pc2['components'])
    assert tuple(e['type'] for e in pc2['actions']) == (
        'Snapshot',  # Second Snapshot
        'RateComputer',
        'Remove'  # the processor we added in 2.
    )
    # p1c2s has Snapshot, Remove and Add
    p1c2s, _ = user.get(res=m.Device, item=pc1['components'][0]['id'])
    assert tuple(get_actions_info(p1c2s['actions'])) == (
        ('BenchmarkProcessor', []),  # first BenchmarkProcessor
        ('Snapshot', ['p1c1s', 'p1c2s', 'p1c3s']),  # First Snapshot to PC1
        ('RateComputer', ['p1c1s', 'p1c2s', 'p1c3s']),
        ('Snapshot', ['p1c2s', 'p2c1s']),  # Second Snapshot to PC2
        ('Remove', ['p1c2s']),  # ...which caused p1c2s to be removed form PC1
        ('RateComputer', ['p1c2s', 'p2c1s']),
        ('Snapshot', ['p1c2s', 'p1c3s']),  # The third Snapshot to PC1
        ('Remove', ['p1c2s']),  # ...which caused p1c2 to be removed from PC2
        ('RateComputer', ['p1c2s', 'p1c3s'])
    )

    # We register the first device but without the processor,
    # adding a graphic card and adding a new component
    s4 = file('4-first-device-but-removing-processor.snapshot-and-adding-graphic-card')
    snapshot4 = snapshot_and_check(user, s4, ('RateComputer',), perform_second_snapshot=False)
    pc1, _ = user.get(res=m.Device, item=pc1_id)
    pc2, _ = user.get(res=m.Device, item=pc2_id)
    # Check if the update_timestamp is updated
    update3_pc2 = pc2['updated']
    update4_pc1 = pc1['updated']
    assert not update4_pc1 in [update1_pc1, update2_pc1, update3_pc1]
    assert update3_pc2 == update2_pc2
    # PC 0: p1c3s, p1c4s. PC1: p2c1s
    assert {c['serialNumber'] for c in pc1['components']} == {'p1c3s'}
    assert all(c['parent'] == pc1_id for c in pc1['components'])
    # This last Action only
    assert get_actions_info(pc1['actions'])[-1] == ('RateComputer', ['p1c3s'])
    # PC2
    # We haven't changed PC2
    assert tuple(c['serialNumber'] for c in pc2['components']) == ('p2c1s',)
    assert all(c['parent'] == pc2_id for c in pc2['components'])

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
    assert response_snapshot['severity'] == 'Warning'
    assert response_status.status_code == 201


@pytest.mark.mvp
def test_snapshot_mismatch_id():
    """Tests uploading a device with an ID from another device."""
    # Note that this won't happen as in this new version
    # the ID is not used in the Snapshot process
    pass


@pytest.mark.mvp
def test_snapshot_tag_inner_tag(user: UserClient, tag_id: str, app: Devicehub):
    """Tests a posting Snapshot with a local tag."""
    b = file('basic.snapshot')
    b['device']['tags'] = [{'type': 'Tag', 'id': tag_id}]

    snapshot_and_check(user, b,
                       action_types=(RateComputer.t, BenchmarkProcessor.t, VisualTest.t))
    with app.app_context():
        tag = Tag.query.one()  # type: Tag
        assert tag.device_id == 1, 'Tag should be linked to the first device'


@pytest.mark.mvp
def test_snapshot_tag_inner_tag_mismatch_between_tags_and_hid(user: UserClient, tag_id: str):
    """Ensures one device cannot 'steal' the tag from another one."""
    pc1 = file('basic.snapshot')
    pc1['device']['tags'] = [{'type': 'Tag', 'id': tag_id}]
    user.post(pc1, res=Snapshot)
    pc2 = file('1-device-with-components.snapshot')
    user.post(pc2, res=Snapshot)  # PC2 uploads well
    pc2['device']['tags'] = [{'type': 'Tag', 'id': tag_id}]  # Set tag from pc1 to pc2
    user.post(pc2, res=Snapshot, status=MismatchBetweenTagsAndHid)


@pytest.mark.mvp
def test_snapshot_different_properties_same_tags(user: UserClient, tag_id: str):
    """Tests a snapshot performed to device 1 with tag A and then to
    device 2 with tag B. Both don't have HID but are different type.
    Devicehub must fail the Snapshot.
    """
    # 1. Upload PC1 without hid but with tag
    pc1 = file('basic.snapshot')
    pc1['device']['tags'] = [{'type': 'Tag', 'id': tag_id}]
    del pc1['device']['serialNumber']
    user.post(pc1, res=Snapshot)
    # 2. Upload PC2 without hid, a different characteristic than PC1, but with same tag
    pc2 = file('basic.snapshot')
    pc2['uuid'] = uuid4()
    pc2['device']['tags'] = pc1['device']['tags']
    # pc2 model is unknown but pc1 model is set = different property
    del pc2['device']['model']
    user.post(pc2, res=Snapshot, status=MismatchBetweenProperties)


@pytest.mark.mvp
def test_snapshot_upload_twice_uuid_error(user: UserClient):
    pc1 = file('basic.snapshot')
    user.post(pc1, res=Snapshot)
    user.post(pc1, res=Snapshot, status=UniqueViolation)


@pytest.mark.mvp
def test_snapshot_component_containing_components(user: UserClient):
    """There is no reason for components to have components and when
    this happens it is always an error.

    This test avoids this until an appropriate use-case is presented.
    """
    s = file('basic.snapshot')
    s['device'] = {
        'type': 'Processor',
        'serialNumber': 'foo',
        'manufacturer': 'bar',
        'model': 'baz'
    }
    user.post(s, res=Snapshot, status=ValidationError)


@pytest.mark.mvp
def test_erase_privacy_standards_endtime_sort(user: UserClient):
    """Tests a Snapshot with EraseSectors and the resulting privacy
    properties.

    This tests ensures that only the last erasure is picked up, as
    erasures have always custom endTime value set.
    """
    s = file('erase-sectors.snapshot')
    assert s['components'][0]['actions'][0]['endTime'] == '2018-06-01T09:12:06+02:00'
    snapshot = snapshot_and_check(user, s, action_types=(
        EraseSectors.t,
        BenchmarkDataStorage.t,
        BenchmarkProcessor.t,
        RateComputer.t,
        EreusePrice.t
    ), perform_second_snapshot=False)
    # Perform a new snapshot changing the erasure time, as if
    # it is a new erasure performed after.
    erase = next(e for e in snapshot['actions'] if e['type'] == EraseSectors.t)
    assert erase['endTime'] == '2018-06-01T07:12:06+00:00'
    s['uuid'] = uuid4()
    s['components'][0]['actions'][0]['endTime'] = '2018-06-01T07:14:00+00:00'
    snapshot = snapshot_and_check(user, s, action_types=(
        EraseSectors.t,
        BenchmarkDataStorage.t,
        BenchmarkProcessor.t,
        RateComputer.t,
        EreusePrice.t
    ), perform_second_snapshot=False)

    # The actual test
    storage = next(e for e in snapshot['components'] if e['type'] == SolidStateDrive.t)
    storage, _ = user.get(res=m.Device, item=storage['id'])  # Let's get storage actions too
    # order: endTime ascending
    #        erasure1/2 have an user defined time and others actions endTime = created
    erasure1, erasure2, benchmark_hdd1, _snapshot1, _, _, benchmark_hdd2, _snapshot2 = storage['actions'][:8]
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
    pc, _ = user.get(res=m.Device, item=snapshot['device']['id'])
    assert pc['privacy'] == [storage['privacy']]

    # Let's try a second erasure with an error
    s['uuid'] = uuid4()
    s['components'][0]['actions'][0]['severity'] = 'Error'
    snapshot, _ = user.post(s, res=Snapshot)
    storage, _ = user.get(res=m.Device, item=storage['id'])
    assert storage['hid'] == 'solidstatedrive-c1mr-c1ml-c1s'
    assert storage['privacy']['type'] == 'EraseSectors'
    pc, _ = user.get(res=m.Device, item=snapshot['device']['id'])
    assert pc['privacy'] == [storage['privacy']]


def test_test_data_storage(user: UserClient):
    """Tests a Snapshot with EraseSectors."""
    s = file('erase-sectors-2-hdd.snapshot')
    snapshot, _ = user.post(res=Snapshot, data=s)
    incidence_test = next(
        ev for ev in snapshot['actions']
        if ev.get('reallocatedSectorCount', None) == 15
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


def snapshot_and_check(user: UserClient,
                       input_snapshot: dict,
                       action_types: Tuple[str, ...] = tuple(),
                       perform_second_snapshot=True) -> dict:
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
    snapshot, _ = user.post(res=Snapshot, data=input_snapshot)
    assert all(e['type'] in action_types for e in snapshot['actions'])
    assert len(snapshot['actions']) == len(action_types)
    # Ensure there is no Remove action after the first Add
    found_add = False
    for action in snapshot['actions']:
        if action['type'] == 'Add':
            found_add = True
        if found_add:
            assert action['type'] != 'Receive', 'All Remove actions must be before the Add ones'
    assert input_snapshot['device']
    assert_similar_device(input_snapshot['device'], snapshot['device'])
    if input_snapshot.get('components', None):
        assert_similar_components(input_snapshot['components'], snapshot['components'])
    assert all(c['parent'] == snapshot['device']['id'] for c in snapshot['components']), \
        'Components must be in their parent'
    if perform_second_snapshot:
        if 'uuid' in input_snapshot:
            input_snapshot['uuid'] = uuid4()
        return snapshot_and_check(user, input_snapshot, action_types,
                                  perform_second_snapshot=False)
    else:
        return snapshot


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
    """ This test check if works the function save_snapshot_in_file """
    snapshot_no_hid = file('basic.snapshot.nohid')
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
def test_save_snapshot_with_debug(app: Devicehub, user: UserClient):
    """ This test check if works the function save_snapshot_in_file """
    snapshot_file = file('basic.snapshot.with_debug')
    debug = snapshot_file['debug']
    user.post(res=Snapshot, data=snapshot_file)

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
def test_backup_snapshot_with_errors(app: Devicehub, user: UserClient):
    """ This test check if the file snapshot is create when some snapshot is wrong """
    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'], 'errors')
    snapshot_no_hid = file('basic.snapshot.badly_formed')
    uuid = snapshot_no_hid['uuid']

    snapshot = {'software': '', 'version': '', 'uuid': ''}
    with pytest.raises(KeyError):
        response = user.post(res=Snapshot, data=snapshot_no_hid)

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
    """ This test check if the file snapshot is create when some snapshot is wrong """
    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'], 'errors')
    snapshot_error = file('failed.snapshot.500.missing-cpu-benchmark')
    uuid = snapshot_error['uuid']

    snapshot = {'software': '', 'version': '', 'uuid': ''}
    with pytest.raises(TypeError):
        user.post(res=Snapshot, data=snapshot_error)

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
    """ This test check if the file snapshot is create when some snapshot is wrong """
    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'], 'errors')
    snapshot_error = file('failed.snapshot.500.missing-hdd-benchmark')
    uuid = snapshot_error['uuid']

    snapshot = {'software': '', 'version': '', 'uuid': ''}
    with pytest.raises(TypeError):
        user.post(res=Snapshot, data=snapshot_error)

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
def test_snapshot_failed_null_chassis(app: Devicehub, user: UserClient):
    """ This test check if the file snapshot is create when some snapshot is wrong """
    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'], 'errors')
    snapshot_error = file('failed.snapshot.422.null-chassis')
    uuid = snapshot_error['uuid']

    snapshot = {'software': '', 'version': '', 'uuid': ''}
    with pytest.raises(TypeError):
        user.post(res=Snapshot, data=snapshot_error)

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
def test_snapshot_failed_missing_chassis(app: Devicehub, user: UserClient):
    """ This test check if the file snapshot is create when some snapshot is wrong """
    tmp_snapshots = app.config['TMP_SNAPSHOTS']
    path_dir_base = os.path.join(tmp_snapshots, user.user['email'], 'errors')
    snapshot_error = file('failed.snapshot.422.missing-chassis')
    uuid = snapshot_error['uuid']

    snapshot = {'software': '', 'version': '', 'uuid': ''}
    with pytest.raises(TypeError):
        user.post(res=Snapshot, data=snapshot_error)

    files = [x for x in os.listdir(path_dir_base) if uuid in x]
    if files:
        path_snapshot = os.path.join(path_dir_base, files[0])
        with open(path_snapshot) as file_snapshot:
            snapshot = json.loads(file_snapshot.read())

        shutil.rmtree(tmp_snapshots)

    assert snapshot['software'] == snapshot_error['software']
    assert snapshot['version'] == snapshot_error['version']
    assert snapshot['uuid'] == uuid

