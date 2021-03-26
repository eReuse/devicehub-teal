import os
import ipaddress
import json
import shutil
import copy
import pytest

from datetime import datetime, timedelta
from dateutil.tz import tzutc
from decimal import Decimal
from typing import Tuple, Type

from flask import current_app as app, g
from sqlalchemy.util import OrderedSet
from teal.enums import Currency, Subdivision

from ereuse_devicehub.db import db
from ereuse_devicehub.client import UserClient, Client
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources import enums
from ereuse_devicehub.resources.action import models
from ereuse_devicehub.resources.device import states
from ereuse_devicehub.resources.device.models import Desktop, Device, GraphicCard, HardDrive, \
    RamModule, SolidStateDrive
from ereuse_devicehub.resources.enums import ComputerChassis, Severity, TestDataStorageLength
from tests import conftest
from tests.conftest import create_user, file


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_author():
    """Checks the default created author.

    Note that the author can be accessed after inserting the row.
    """
    user = create_user()
    g.user = user
    e = models.ActionWithOneDevice(device=Device())
    db.session.add(e)
    assert e.author is None
    assert e.author_id is None
    db.session.commit()
    assert e.author == user


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_erase_basic():
    erasure = models.EraseBasic(
        device=HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        steps=[
            models.StepZero(**conftest.T),
            models.StepRandom(**conftest.T)
        ],
        **conftest.T
    )
    db.session.add(erasure)
    db.session.commit()
    db_erasure = models.EraseBasic.query.one()
    assert erasure == db_erasure
    assert next(iter(db_erasure.device.actions)) == erasure
    assert not erasure.standards, 'EraseBasic themselves do not have standards'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_validate_device_data_storage():
    """Checks the validation for data-storage-only actions works."""
    # We can't set a GraphicCard
    with pytest.raises(TypeError,
                       message='EraseBasic.device must be a DataStorage '
                               'but you passed <GraphicCard None model=\'foo-bar\' S/N=\'foo\'>'):
        models.EraseBasic(
            device=GraphicCard(serial_number='foo', manufacturer='bar', model='foo-bar'),
            clean_with_zeros=True,
            **conftest.T
        )


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_erase_sectors_steps_erasure_standards_hmg_is5():
    erasure = models.EraseSectors(
        device=SolidStateDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        steps=[
            models.StepZero(**conftest.T),
            models.StepRandom(**conftest.T),
            models.StepRandom(**conftest.T)
        ],
        **conftest.T
    )
    db.session.add(erasure)
    db.session.commit()
    db_erasure = models.EraseSectors.query.one()
    # Steps are in order
    assert db_erasure.steps[0].num == 0
    assert db_erasure.steps[1].num == 1
    assert db_erasure.steps[2].num == 2
    assert {enums.ErasureStandards.HMG_IS5} == erasure.standards


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_test_data_storage_working():
    """Tests TestDataStorage with the resulting properties in Device."""
    hdd = HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar')
    test = models.TestDataStorage(
        device=hdd,
        severity=Severity.Error,
        elapsed=timedelta(minutes=25),
        length=TestDataStorageLength.Short,
        status=':-(',
        lifetime=timedelta(days=120)
    )
    db.session.add(test)
    db.session.flush()
    assert hdd.working == [test]
    assert not hdd.problems
    # Add new test overriding the first test in the problems
    # / working condition
    test2 = models.TestDataStorage(
        device=hdd,
        severity=Severity.Warning,
        elapsed=timedelta(minutes=25),
        length=TestDataStorageLength.Short,
        status=':-(',
        lifetime=timedelta(days=120)
    )
    db.session.add(test2)
    db.session.flush()
    assert hdd.working == [test2]
    assert hdd.problems == []


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_install():
    hdd = HardDrive(serial_number='sn')
    install = models.Install(name='LinuxMint 18.04 es',
                             elapsed=timedelta(seconds=25),
                             device=hdd)
    db.session.add(install)
    db.session.commit()


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_update_components_action_one():
    computer = Desktop(serial_number='sn1',
                       model='ml1',
                       manufacturer='mr1',
                       chassis=ComputerChassis.Tower)
    hdd = HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar')
    computer.components.add(hdd)

    # Add action
    test = models.StressTest(elapsed=timedelta(minutes=1))
    computer.actions_one.add(test)
    assert test.device == computer
    assert next(iter(test.components)) == hdd, 'Action has to have new components'

    # Remove action
    computer.actions_one.clear()
    assert not test.device
    assert not test.components, 'Action has to loose the components'

    # If we add a component to a device AFTER assigning the action
    # to the device, the action doesn't get the new component
    computer.actions_one.add(test)
    ram = RamModule()
    computer.components.add(ram)
    assert len(test.components) == 1


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_update_components_action_multiple():
    computer = Desktop(serial_number='sn1',
                       model='ml1',
                       manufacturer='mr1',
                       chassis=ComputerChassis.Tower)
    hdd = HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar')
    computer.components.add(hdd)

    ready = models.Ready()
    assert not ready.devices
    assert not ready.components

    # Add
    computer.actions_multiple.add(ready)
    assert ready.devices == OrderedSet([computer])
    assert next(iter(ready.components)) == hdd

    # Remove
    computer.actions_multiple.remove(ready)
    assert not ready.devices
    assert not ready.components

    # init / replace collection
    ready.devices = OrderedSet([computer])
    assert ready.devices
    assert ready.components


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_update_parent():
    computer = Desktop(serial_number='sn1',
                       model='ml1',
                       manufacturer='mr1',
                       chassis=ComputerChassis.Tower)
    hdd = HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar')
    computer.components.add(hdd)

    # Add
    benchmark = models.BenchmarkDataStorage()
    benchmark.device = hdd
    assert benchmark.parent == computer
    assert not benchmark.components

    # Remove
    benchmark.device = None
    assert not benchmark.parent


@pytest.mark.mvp
@pytest.mark.parametrize('action_model_state',
                         (pytest.param(ams, id=ams[0].__class__.__name__)
                          for ams in [
                              (models.ToRepair, states.Physical.ToBeRepaired),
                              (models.Repair, states.Physical.Repaired),
                              (models.ToPrepare, states.Physical.Preparing),
                              (models.Ready, states.Physical.Ready),
                              (models.Prepare, states.Physical.Prepared)
                          ]))
def test_generic_action(action_model_state: Tuple[models.Action, states.Trading],
                        user: UserClient):
    """Tests POSTing all generic actions."""
    action_model, state = action_model_state
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    action = {'type': action_model.t, 'devices': [snapshot['device']['id']]}
    action, _ = user.post(action, res=models.Action)
    assert action['devices'][0]['id'] == snapshot['device']['id']
    device, _ = user.get(res=Device, item=snapshot['device']['devicehubID'])
    assert device['actions'][-1]['id'] == action['id']
    assert device['physical'] == state.name
    # Check if the update of device is changed
    assert snapshot['device']['updated'] != device['updated']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live(user: UserClient, client: Client, app: Devicehub):
    """Tests inserting a Live into the database and GETting it."""
    acer = file('acer.happy.battery.snapshot')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id], "description": "aaa",
                    "finalUserCode": "abcdefjhi",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_request)
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['lifetime'] += 1000
    acer.pop('elapsed')
    acer['licence_version'] = '1.0.0'
    snapshot, _ = client.post(acer, res=models.Live)
    db_device = Device.query.filter_by(id=device_id).one()
    action_live = [a for a in db_device.actions if a.type == 'Live']
    assert len(action_live) == 1
    assert action_live[0].usage_time_hdd == timedelta(hours=hdd_action['lifetime'])
    assert action_live[0].usage_time_allocate == timedelta(hours=1000)
    assert action_live[0].final_user_code == post_request['finalUserCode']
    assert action_live[0].serial_number == 'wd-wx11a80w7430'
    assert action_live[0].licence_version == '1.0'
    assert str(action_live[0].snapshot_uuid) == acer['uuid']
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live_example(user: UserClient, client: Client, app: Devicehub):
    """Tests inserting a Live into the database and GETting it."""
    acer = file('snapshotLive')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id], "description": "aaa",
                    "finalUserCode": "abcdefjhi",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_request)

    acer = file('live')
    live, _ = client.post(acer, res=models.Live)
    db_device = Device.query.filter_by(id=device_id).one()
    action_live = [a for a in db_device.actions if a.type == 'Live']
    assert len(action_live) == 1
    assert str(action_live[0].snapshot_uuid) == acer['uuid']
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live_two_users(user: UserClient, user2: UserClient, client: Client, app: Devicehub):
    """Tests inserting a Live into the database and GETting it."""
    acer = file('snapshotLive')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    acer2 = file('snapshotLive')
    acer2['uuid'] = '3b6a9288-0ba6-4bdd-862a-2b1f660e7115'
    snapshot2, _ = user2.post(acer2, res=models.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id], "description": "aaa",
                    "finalUserCode": "abcdefjhi",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_request)

    acer = file('live')
    live, _ = client.post(acer, res=models.Live)
    db_device = Device.query.filter_by(id=device_id).one()
    action_live = [a for a in db_device.actions if a.type == 'Live']
    assert len(action_live) == 1
    assert str(action_live[0].snapshot_uuid) == acer['uuid']
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live_two_allocated(user: UserClient, user2: UserClient, client: Client, app: Devicehub):
    """Tests inserting a Live into the database and GETting it."""
    acer = file('snapshotLive')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    acer2 = file('snapshotLive')
    acer2['uuid'] = '3b6a9288-0ba6-4bdd-862a-2b1f660e7115'
    snapshot2, _ = user2.post(acer2, res=models.Snapshot)
    device_id = snapshot['device']['id']
    device_id2 = snapshot2['device']['id']
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id], "description": "aaa",
                    "finalUserCode": "abcdefjhi",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }
    post_request2 = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id2], "description": "aaa",
                    "finalUserCode": "abcdefjhi",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_request)
    user2.post(res=models.Allocate, data=post_request2)

    acer = file('live')
    live, _ = client.post(acer, res=models.Live, status=422)
    message = 'Expected only one Device but multiple where found'
    assert live['message'] == message
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live_without_TestDataStorage(user: UserClient, client: Client, app: Devicehub):
    """Tests inserting a Live into the database and GETting it.
       If the live don't have a TestDataStorage, then save live and response None
    """
    acer = file('acer.happy.battery.snapshot')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    device_id = snapshot['device']['id']
    db_device = Device.query.filter_by(id=1).one()
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id], "description": "aaa",
                    "finalUserCode": "abcdefjhi",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_request)
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    actions = [a for a in acer['components'][7]['actions'] if a['type'] != 'TestDataStorage']
    acer['components'][7]['actions'] = actions
    acer.pop('elapsed')
    acer['licence_version'] = '1.0.0'
    live, _ = client.post(acer, res=models.Live)
    assert live['severity'] == 'Warning'
    description = "We don't found any TestDataStorage for disk sn: wd-wx11a80w7430"
    assert live['description'] == description
    db_live = models.Live.query.filter_by(id=live['id']).one()
    assert db_live.usage_time_hdd is None
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live_without_hdd_1(user: UserClient, client: Client, app: Devicehub):
    """Tests inserting a Live into the database and GETting it.
       The snapshot have hdd but the live no, and response 404
    """
    acer = file('acer.happy.battery.snapshot')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    device_id = snapshot['device']['id']
    db_device = Device.query.filter_by(id=1).one()
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id], "description": "aaa",
                    "finalUserCode": "abcdefjhi",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_request)
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    components = [a for a in acer['components'] if a['type'] != 'HardDrive']
    acer['components'] = components
    acer.pop('elapsed')
    acer['licence_version'] = '1.0.0'
    response, _ = client.post(acer, res=models.Live, status=404)
    assert "The There aren't any disk in this device" in response['message']
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live_without_hdd_2(user: UserClient, client: Client, app: Devicehub):
    """Tests inserting a Live into the database and GETting it.
       The snapshot haven't hdd and the live neither, and response 404
    """
    acer = file('acer.happy.battery.snapshot')
    components = [a for a in acer['components'] if a['type'] != 'HardDrive']
    acer['components'] = components
    snapshot, _ = user.post(acer, res=models.Snapshot)
    device_id = snapshot['device']['id']
    db_device = Device.query.filter_by(id=1).one()
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id], "description": "aaa",
                    "finalUserCode": "abcdefjhi",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_request)
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    acer.pop('elapsed')
    acer['licence_version'] = '1.0.0'
    response, _ = client.post(acer, res=models.Live, status=404)
    assert "The There aren't any disk in this device" in response['message']
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live_without_hdd_3(user: UserClient, client: Client, app: Devicehub):
    """Tests inserting a Live into the database and GETting it.
       The snapshot haven't hdd and the live have, and save the live
       with usage_time_allocate == 0
    """
    acer = file('acer.happy.battery.snapshot')
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    components = [a for a in acer['components'] if a['type'] != 'HardDrive']
    acer['components'] = components
    snapshot, _ = user.post(acer, res=models.Snapshot)
    device_id = snapshot['device']['id']
    db_device = Device.query.filter_by(id=1).one()
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id], "description": "aaa",
                    "finalUserCode": "abcdefjhi",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_request)
    acer = file('acer.happy.battery.snapshot')
    acer.pop('elapsed')
    acer['licence_version'] = '1.0.0'
    live, _ = client.post(acer, res=models.Live)
    assert live['severity'] == 'Warning'
    description = "Don't exist one previous live or snapshot as reference"
    assert live['description'] == description
    db_live = models.Live.query.filter_by(id=live['id']).one()
    assert str(db_live.usage_time_hdd) == '195 days, 12:00:00'
    assert str(db_live.usage_time_allocate) == '0:00:00'
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live_with_hdd_with_old_time(user: UserClient, client: Client, app: Devicehub):
    """Tests inserting a Live into the database and GETting it.
       The snapshot hdd have a lifetime higher than lifetime of the live action
       save the live with usage_time_allocate == 0
    """
    acer = file('acer.happy.battery.snapshot')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    device_id = snapshot['device']['id']
    db_device = Device.query.filter_by(id=1).one()
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id], "description": "aaa",
                    "finalUserCode": "abcdefjhi",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_request)
    acer = file('acer.happy.battery.snapshot')
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    action = [a for a in acer['components'][7]['actions'] if a['type'] == 'TestDataStorage']
    action[0]['lifetime'] -= 100
    acer.pop('elapsed')
    acer['licence_version'] = '1.0.0'
    live, _ = client.post(acer, res=models.Live)
    assert live['severity'] == 'Warning'
    description = "The difference with the last live/snapshot is negative"
    assert live['description'] == description
    db_live = models.Live.query.filter_by(id=live['id']).one()
    assert str(db_live.usage_time_hdd) == '191 days, 8:00:00'
    assert str(db_live.usage_time_allocate) == '0:00:00'
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live_search_last_allocate(user: UserClient, client: Client, app: Devicehub):
    """Tests inserting a Live into the database and GETting it.
    """
    acer = file('acer.happy.battery.snapshot')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id], "description": "aaa",
                    "finalUserCode": "abcdefjhi",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_request)
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['lifetime'] += 1000
    acer.pop('elapsed')
    acer['licence_version'] = '1.0.0'
    live, _ = client.post(acer, res=models.Live)
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec4"
    actions = [a for a in acer['components'][7]['actions'] if a['type'] != 'TestDataStorage']
    acer['components'][7]['actions'] = actions
    live, _ = client.post(acer, res=models.Live)
    assert live['usageTimeAllocate'] == 1000
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
def test_save_live_json(app: Devicehub, user: UserClient, client: Client):
    """ This test check if works the function save_snapshot_in_file """
    acer = file('acer.happy.battery.snapshot')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    debug = 'AAA'
    acer['debug'] = debug
    device_id = snapshot['device']['id']
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id], "description": "aaa",
                    "finalUserCode": "abcdefjhi",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_request)
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['lifetime'] += 1000
    acer.pop('elapsed')
    acer['licence_version'] = '1.0.0'
    live, _ = client.post(acer, res=models.Live)

    tmp_snapshots = app.config['TMP_LIVES']
    path_dir_base = os.path.join(tmp_snapshots)

    uuid = acer['uuid']
    files = [x for x in os.listdir(path_dir_base) if uuid in x]

    snapshot = {'debug': ''}
    if files:
        path_snapshot = os.path.join(path_dir_base, files[-1])
        with open(path_snapshot) as file_snapshot:
            snapshot = json.loads(file_snapshot.read())

    shutil.rmtree(tmp_snapshots)

    assert snapshot['debug'] == debug
    

@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_licences(client: Client):
    """Tests inserting a Live into the database and GETting it.
    """
    licences, _ = client.get('/licences/')
    licences = json.loads(licences)
    assert licences[0]['USOdyPrivacyPolicyVersion'] == '1.0.0'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_allocate(user: UserClient):
    """ Tests allocate """
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device_id = snapshot['device']['id']
    devicehub_id = snapshot['device']['devicehubID']
    post_request = {"transaction": "ccc", 
                    "finalUserCode": "aabbcc",
                    "name": "John", 
                    "severity": "Info",
                    "endUsers": 1,
                    "devices": [device_id], 
                    "description": "aaa",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00",
    }

    allocate, _ = user.post(res=models.Allocate, data=post_request)
    # Normal allocate
    device, _ = user.get(res=Device, item=devicehub_id)
    assert device['allocated'] == True
    action = [a for a in device['actions'] if a['type'] == 'Allocate'][0]
    assert action['transaction'] == allocate['transaction']
    assert action['finalUserCode'] == allocate['finalUserCode']
    assert action['created'] == allocate['created']
    assert action['startTime'] == allocate['startTime']
    assert action['endUsers'] == allocate['endUsers']
    assert action['name'] == allocate['name']

    post_bad_request1 = copy.copy(post_request)
    post_bad_request1['endUsers'] = 2
    post_bad_request2 = copy.copy(post_request)
    post_bad_request2['startTime'] = "2020-11-01T02:00:00+00:01"
    post_bad_request3 = copy.copy(post_request)
    post_bad_request3['transaction'] = "aaa"
    res1, _ = user.post(res=models.Allocate, data=post_bad_request1, status=422)
    res2, _ = user.post(res=models.Allocate, data=post_bad_request2, status=422)
    res3, _ = user.post(res=models.Allocate, data=post_bad_request3, status=422)
    for r in (res1, res2, res3):
        assert r['code'] == 422
        assert r['type'] == 'ValidationError'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_allocate_bad_dates(user: UserClient):
    """ Tests allocate """
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device_id = snapshot['device']['id']
    delay = timedelta(days=30)
    future = datetime.now().replace(tzinfo=tzutc()) + delay
    post_request = {"transaction": "ccc", 
                    "finalUserCode": "aabbcc",
                    "name": "John", 
                    "severity": "Info",
                    "end_users": 1,
                    "devices": [device_id], 
                    "description": "aaa",
                    "start_time": future,
    }

    res, _ = user.post(res=models.Allocate, data=post_request, status=422)
    assert res['code'] == 422
    assert res['type'] == 'ValidationError'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_deallocate(user: UserClient):
    """ Tests deallocate """
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device_id = snapshot['device']['id']
    devicehub_id = snapshot['device']['devicehubID']
    post_deallocate = {"startTime": "2020-11-01T02:00:00+00:00",
                       "transaction": "ccc",
                       "devices": [device_id]
    }
    res, _ = user.post(res=models.Deallocate, data=post_deallocate, status=422)
    assert res['code'] == 422
    assert res['type'] == 'ValidationError'
    post_allocate = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "devices": [device_id], "description": "aaa",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_allocate)
    device, _ = user.get(res=Device, item=devicehub_id)
    assert device['allocated'] == True
    deallocate, _ = user.post(res=models.Deallocate, data=post_deallocate)
    assert deallocate['startTime'] == post_deallocate['startTime']
    assert deallocate['devices'][0]['id'] == device_id
    assert deallocate['devices'][0]['allocated'] == False
    res, _ = user.post(res=models.Deallocate, data=post_deallocate, status=422)
    assert res['code'] == 422
    assert res['type'] == 'ValidationError'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_deallocate_bad_dates(user: UserClient):
    """ Tests deallocate with bad date of start_time """
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device_id = snapshot['device']['id']
    delay  = timedelta(days=30)
    future = datetime.now().replace(tzinfo=tzutc()) + delay
    post_deallocate = {"startTime": future,
                       "devices": [device_id]
    }
    post_allocate = {"devices": [device_id], "description": "aaa",
                     "startTime": "2020-11-01T02:00:00+00:00"
    }

    user.post(res=models.Allocate, data=post_allocate)
    res, _ = user.post(res=models.Deallocate, data=post_deallocate, status=422)
    assert res['code'] == 422
    assert res['type'] == 'ValidationError'


@pytest.mark.mvp
@pytest.mark.parametrize('action_model_state',
                         (pytest.param(ams, id=ams[0].__name__)
                          for ams in [
                              (models.MakeAvailable, states.Trading.Available),
                              (models.Sell, states.Trading.Sold),
                              (models.Donate, states.Trading.Donated),
                              (models.Rent, states.Trading.Renting),
                              (models.DisposeProduct, states.Trading.ProductDisposed)
                          ]))
def test_trade(action_model_state: Tuple[Type[models.Action], states.Trading], user: UserClient):
    """Tests POSTing all Trade actions."""
    # todo missing None states.Trading for after cancelling renting, for example
    # Remove this test
    action_model, state = action_model_state
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    action = {
        'type': action_model.t,
        'devices': [snapshot['device']['id']]
    }
    if issubclass(action_model, models.Trade):
        action['to'] = user.user['individuals'][0]['id']
        action['shippingDate'] = '2018-06-29T12:28:54'
        action['invoiceNumber'] = 'ABC'
    action, _ = user.post(action, res=models.Action)
    assert action['devices'][0]['id'] == snapshot['device']['id']
    device, _ = user.get(res=Device, item=snapshot['device']['devicehubID'])
    assert device['actions'][-1]['id'] == action['id']
    assert device['trading'] == state.name


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_price_custom():
    computer = Desktop(serial_number='sn1', model='ml1', manufacturer='mr1',
                       chassis=ComputerChassis.Docking)
    price = models.Price(price=Decimal(25.25), currency=Currency.EUR)
    price.device = computer
    assert computer.price == price
    db.session.add(computer)
    db.session.commit()

    client = UserClient(app, 'foo@foo.com', 'foo', response_wrapper=app.response_class)
    client.login()
    p, _ = client.get(res=models.Action, item=str(price.id))
    assert p['device']['id'] == price.device.id == computer.id
    assert p['price'] == 25.25
    assert p['currency'] == Currency.EUR.name == 'EUR'

    c, _ = client.get(res=Device, item=computer.devicehub_id)
    assert c['price']['id'] == p['id']


@pytest.mark.mvp
def test_price_custom_client(user: UserClient):
    """As test_price_custom but creating the price through the API."""
    s = file('basic.snapshot')
    snapshot, _ = user.post(s, res=models.Snapshot)
    price, _ = user.post({
        'type': 'Price',
        'price': 25,
        'currency': Currency.EUR.name,
        'device': snapshot['device']['id']
    }, res=models.Action)
    assert 25 == price['price']
    assert Currency.EUR.name == price['currency']

    device, _ = user.get(res=Device, item=price['device']['devicehubID'])
    assert 25 == device['price']['price']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_erase_physical():
    erasure = models.ErasePhysical(
        device=HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        method=enums.PhysicalErasureMethod.Disintegration
    )
    db.session.add(erasure)
    db.session.commit()
