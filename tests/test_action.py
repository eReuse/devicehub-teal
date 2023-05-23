import copy
import json
import os
import shutil
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from json.decoder import JSONDecodeError
from typing import Tuple

import pytest
from dateutil.tz import tzutc
from flask import current_app as app
from flask import g
from pytest import raises
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources import enums
from ereuse_devicehub.resources.action import models
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.device import states
from ereuse_devicehub.resources.device.models import (
    Desktop,
    Device,
    GraphicCard,
    HardDrive,
    RamModule,
    SolidStateDrive,
)
from ereuse_devicehub.resources.enums import (
    ComputerChassis,
    Severity,
    TestDataStorageLength,
)
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.tradedocument.models import TradeDocument
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.teal.enums import Currency
from tests import conftest
from tests.conftest import create_user, file, json_encode, yaml2json


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
        steps=[models.StepZero(**conftest.T), models.StepRandom(**conftest.T)],
        **conftest.T,
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
    with pytest.raises(TypeError):
        models.EraseBasic(
            device=GraphicCard(
                serial_number='foo', manufacturer='bar', model='foo-bar'
            ),
            clean_with_zeros=True,
            **conftest.T,
        )
        pytest.fail(
            'EraseBasic.device must be a DataStorage '
            'but you passed <GraphicCard None model=\'foo-bar\' S/N=\'foo\'>'
        )


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_erase_sectors_steps_erasure_standards_hmg_is5():
    erasure = models.EraseSectors(
        device=SolidStateDrive(
            serial_number='foo', manufacturer='bar', model='foo-bar'
        ),
        steps=[
            models.StepZero(**conftest.T),
            models.StepRandom(**conftest.T),
            models.StepRandom(**conftest.T),
        ],
        **conftest.T,
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
        lifetime=timedelta(days=120),
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
        lifetime=timedelta(days=120),
    )
    db.session.add(test2)
    db.session.flush()
    assert hdd.working == [test2]
    assert hdd.problems == []


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_install():
    hdd = HardDrive(serial_number='sn')
    install = models.Install(
        name='LinuxMint 18.04 es', elapsed=timedelta(seconds=25), device=hdd
    )
    db.session.add(install)
    db.session.commit()


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_update_components_action_one():
    computer = Desktop(
        serial_number='sn1',
        model='ml1',
        manufacturer='mr1',
        chassis=ComputerChassis.Tower,
    )
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
    computer = Desktop(
        serial_number='sn1',
        model='ml1',
        manufacturer='mr1',
        chassis=ComputerChassis.Tower,
    )
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
    computer = Desktop(
        serial_number='sn1',
        model='ml1',
        manufacturer='mr1',
        chassis=ComputerChassis.Tower,
    )
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
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
@pytest.mark.parametrize(
    'action_model_state',
    (
        pytest.param(ams, id=ams[0].__class__.__name__)
        for ams in [
            (models.ToPrepare, states.Physical.ToPrepare),
            (models.Prepare, states.Physical.Prepare),
            (models.ToRepair, states.Physical.ToRepair),
            (models.Ready, states.Physical.Ready),
        ]
    ),
)
def test_generic_action(
    action_model_state: Tuple[models.ToPrepare, states.Trading], user2: UserClient
):
    """Tests POSTing all generic actions."""
    user = user2
    action_model, state = action_model_state
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    abstract = Device.query.filter(Device.id == snapshot['device']['id']).one()
    real = abstract.binding.device
    action = {'type': action_model.t, 'devices': [real.id]}
    action, _ = user.post(action, res=models.Action)
    assert action['devices'][0]['id'] == real.id
    device, _ = user.get(res=Device, item=real.dhid)
    assert device['actions'][-1]['id'] == action['id']
    assert device['physical'] == state.name
    # Check if the update of device is changed
    assert snapshot['device']['updated'] != device['updated']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
@pytest.mark.parametrize(
    'action_model',
    (
        pytest.param(ams, id=ams.__class__.__name__)
        for ams in [models.Recycling, models.Use, models.Refurbish, models.Management]
    ),
)
def test_simple_status_actions(action_model: models.Action, user2: UserClient):
    """Simple test of status action."""
    user = user2
    snap, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    abstract = Device.query.filter(Device.id == snap['device']['id']).one()
    real = abstract.binding.device

    action = {'type': action_model.t, 'devices': [real.id]}
    action, _ = user.post(action, res=models.Action)
    device, _ = user.get(res=Device, item=real.dhid)
    assert device['actions'][-1]['id'] == action['id']
    assert action['author']['id'] == user.user['id']
    assert action['rol_user']['id'] == user.user['id']


@pytest.mark.mvp
@pytest.mark.parametrize(
    'action_model',
    (
        pytest.param(ams, id=ams.__class__.__name__)
        for ams in [models.Recycling, models.Use, models.Refurbish, models.Management]
    ),
)
def test_outgoinlot_status_actions(
    action_model: models.Action, user: UserClient, user2: UserClient
):
    """Test of status actions in outgoinlot."""
    snap, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device, _ = user.get(res=Device, item=snap['device']['devicehubID'])
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=[('id', device['id'])]
    )

    request_post = {
        'type': 'Trade',
        'devices': [device['id']],
        'userFromEmail': user.email,
        'userToEmail': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    action = {'type': action_model.t, 'devices': [device['id']]}
    action, _ = user.post(action, res=models.Action)
    device, _ = user.get(res=Device, item=snap['device']['devicehubID'])

    assert device['actions'][-1]['id'] == action['id']
    assert action['author']['id'] == user.user['id']
    assert action['rol_user']['id'] == user2.user['id']

    # Remove device from lot
    lot, _ = user.delete(
        {},
        res=Lot,
        item='{}/devices'.format(lot['id']),
        query=[('id', device['id'])],
        status=200,
    )

    action = {'type': action_model.t, 'devices': [device['id']]}
    action, _ = user.post(action, res=models.Action)
    device, _ = user.get(res=Device, item=snap['device']['devicehubID'])

    assert device['actions'][-1]['id'] == action['id']
    assert action['author']['id'] == user.user['id']
    assert action['rol_user']['id'] == user2.user['id']


@pytest.mark.mvp
@pytest.mark.parametrize(
    'action_model',
    (
        pytest.param(ams, id=ams.__class__.__name__)
        for ams in [models.Recycling, models.Use, models.Refurbish, models.Management]
    ),
)
def test_incominglot_status_actions(
    action_model: models.Action, user: UserClient, user2: UserClient
):
    """Test of status actions in outgoinlot."""
    snap, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device, _ = user.get(res=Device, item=snap['device']['devicehubID'])
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=[('id', device['id'])]
    )

    request_post = {
        'type': 'Trade',
        'devices': [device['id']],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    action = {'type': action_model.t, 'devices': [device['id']]}
    action, _ = user.post(action, res=models.Action)
    device, _ = user.get(res=Device, item=snap['device']['devicehubID'])

    assert device['actions'][-1]['id'] == action['id']
    assert action['author']['id'] == user.user['id']
    assert action['rol_user']['id'] == user.user['id']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_history_status_actions(user: UserClient, user2: UserClient):
    """Test for check the status actions."""
    snap, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device = Device.query.filter_by(id=snap['device']['id']).one()

    # Case 1
    action = {'type': models.Recycling.t, 'devices': [device.id]}
    action, _ = user.post(action, res=models.Action)

    assert str(device.actions[-1].id) == action['id']
    assert action['id'] == str(device.status.id)
    assert device.status.t == models.Recycling.t
    assert [action['id']] == [str(ac.id) for ac in device.history_status]

    # Case 2
    action2 = {'type': models.Refurbish.t, 'devices': [device.id]}
    action2, _ = user.post(action2, res=models.Action)
    assert action2['id'] == str(device.status.id)
    assert device.status.t == models.Refurbish.t
    assert [action2['id']] == [str(ac.id) for ac in device.history_status]

    # Case 3
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=[('id', device.id)]
    )

    request_post = {
        'type': 'Trade',
        'devices': [device.id],
        'userFromEmail': user.email,
        'userToEmail': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    action3 = {'type': models.Use.t, 'devices': [device.id]}
    action3, _ = user.post(action3, res=models.Action)
    assert action3['id'] == str(device.status.id)
    assert device.status.t == models.Use.t
    assert [action2['id'], action3['id']] == [
        str(ac.id) for ac in device.history_status
    ]


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_use_changing_owner(user: UserClient, user2: UserClient):
    """Check if is it possible to do a use action for one device
    when you are not the owner.
    """
    snap, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device = Device.query.filter_by(id=snap['device']['id']).one()

    assert device.owner.email == user.email

    # Trade
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=[('id', device.id)]
    )

    request_post = {
        'type': 'Trade',
        'devices': [device.id],
        'userFromEmail': user.email,
        'userToEmail': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    # Doble confirmation and change of owner
    request_confirm = {'type': 'Confirm', 'action': trade.id, 'devices': [device.id]}

    user2.post(res=models.Action, data=request_confirm)
    assert device.owner.email == user2.email

    # Adding action Use
    action3 = {'type': models.Use.t, 'devices': [device.id]}
    action3, _ = user.post(action3, res=models.Action)
    assert action3['id'] == str(device.status.id)
    assert device.status.t == models.Use.t
    assert device.owner.email == user2.email


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_recycling_container(user: UserClient):
    """Test of status action recycling for a container."""
    lot, _ = user.post({'name': 'MyLotOut'}, res=Lot)
    url = ('http://www.ereuse.org/',)
    request_post = {
        'filename': 'test.pdf',
        'hash': 'bbbbbbbb',
        'url': url,
        'weight': 150,
        'lot': lot['id'],
    }
    tradedocument, _ = user.post(res=TradeDocument, data=request_post)
    action = {
        'type': models.Recycling.t,
        'devices': [],
        'documents': [tradedocument['id']],
    }
    action, _ = user.post(action, res=models.Action)
    trade = TradeDocument.query.one()
    assert str(trade.actions[0].id) == action['id']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
@pytest.mark.parametrize(
    'action_model',
    (
        pytest.param(ams, id=ams.__class__.__name__)
        for ams in [models.Recycling, models.Use, models.Refurbish, models.Management]
    ),
)
def test_status_without_lot(action_model: models.Action, user: UserClient):
    """Test of status actions for devices without lot."""
    snap, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    abstract = Device.query.filter_by(id=snap['device']['id']).first()
    device_id = abstract.binding.device.id
    action = {'type': action_model.t, 'devices': [device_id]}
    action, _ = user.post(action, res=models.Action)
    device, _ = user.get(res=Device, item=abstract.dhid)
    assert device['actions'][-1]['id'] == action['id']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
@pytest.mark.parametrize(
    'action_model',
    (
        pytest.param(ams, id=ams.__class__.__name__)
        for ams in [models.Recycling, models.Use, models.Refurbish, models.Management]
    ),
)
def test_status_in_temporary_lot(
    action_model: models.Action, user: UserClient, app: Devicehub
):
    """Test of status actions for devices in a temporary lot."""
    snap, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    abstract = Device.query.filter_by(id=snap['device']['id']).first()
    device_id = abstract.binding.device.id
    lot, _ = user.post({'name': 'MyLotOut'}, res=Lot)
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=[('id', device_id)]
    )
    action = {'type': action_model.t, 'devices': [device_id]}
    action, _ = user.post(action, res=models.Action)
    device, _ = user.get(res=Device, item=abstract.dhid)
    assert device['actions'][-1]['id'] == action['id']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live(user: UserClient, client: Client, app: Devicehub):
    """Tests inserting a Live into the database and GETting it."""
    acer = file('acer.happy.battery.snapshot')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    acer = yaml2json('acer.happy.battery.snapshot')
    device_id = snapshot['device']['id']
    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id],
        "description": "aaa",
        "finalUserCode": "abcdefjhi",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
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
    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id],
        "description": "aaa",
        "finalUserCode": "abcdefjhi",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }

    user.post(res=models.Allocate, data=post_request)

    acer = yaml2json('live')
    live, _ = client.post(acer, res=models.Live)
    db_device = Device.query.filter_by(id=device_id).one()
    action_live = [a for a in db_device.actions if a.type == 'Live']
    assert len(action_live) == 1
    assert str(action_live[0].snapshot_uuid) == acer['uuid']
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live_two_users(
    user: UserClient, user2: UserClient, client: Client, app: Devicehub
):
    """Tests inserting a Live into the database and GETting it."""
    acer = file('snapshotLive')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    acer2 = yaml2json('snapshotLive')
    acer2['uuid'] = '3b6a9288-0ba6-4bdd-862a-2b1f660e7115'
    snapshot2, _ = user2.post(json_encode(acer2), res=models.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id],
        "description": "aaa",
        "finalUserCode": "abcdefjhi",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }

    user.post(res=models.Allocate, data=post_request)

    acer = yaml2json('live')
    live, _ = client.post(acer, res=models.Live)
    db_device = Device.query.filter_by(id=device_id).one()
    action_live = [a for a in db_device.actions if a.type == 'Live']
    assert len(action_live) == 1
    assert str(action_live[0].snapshot_uuid) == acer['uuid']
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_live_two_allocated(
    user: UserClient, user2: UserClient, client: Client, app: Devicehub
):
    """Tests inserting a Live into the database and GETting it."""
    acer = file('snapshotLive')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    acer2 = yaml2json('snapshotLive')
    acer2['uuid'] = '3b6a9288-0ba6-4bdd-862a-2b1f660e7115'
    snapshot2, _ = user2.post(json_encode(acer2), res=models.Snapshot)
    device_id = snapshot['device']['id']
    device_id2 = snapshot2['device']['id']
    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id],
        "description": "aaa",
        "finalUserCode": "abcdefjhi",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }
    post_request2 = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id2],
        "description": "aaa",
        "finalUserCode": "abcdefjhi",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }

    user.post(res=models.Allocate, data=post_request)
    user2.post(res=models.Allocate, data=post_request2)

    acer = yaml2json('live')
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

    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id],
        "description": "aaa",
        "finalUserCode": "abcdefjhi",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }

    user.post(res=models.Allocate, data=post_request)
    acer = yaml2json('acer.happy.battery.snapshot')
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    actions = [
        a for a in acer['components'][7]['actions'] if a['type'] != 'TestDataStorage'
    ]
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

    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id],
        "description": "aaa",
        "finalUserCode": "abcdefjhi",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }

    user.post(res=models.Allocate, data=post_request)
    acer = yaml2json('acer.happy.battery.snapshot')
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
    acer = yaml2json('acer.happy.battery.snapshot')
    components = [a for a in acer['components'] if a['type'] != 'HardDrive']
    acer['components'] = components
    snapshot, _ = user.post(json_encode(acer), res=models.Snapshot)
    device_id = snapshot['device']['id']

    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id],
        "description": "aaa",
        "finalUserCode": "abcdefjhi",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
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
    acer = yaml2json('acer.happy.battery.snapshot')
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    components = [a for a in acer['components'] if a['type'] != 'HardDrive']
    acer['components'] = components
    snapshot, _ = user.post(json_encode(acer), res=models.Snapshot)
    device_id = snapshot['device']['id']

    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id],
        "description": "aaa",
        "finalUserCode": "abcdefjhi",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }

    user.post(res=models.Allocate, data=post_request)
    acer = yaml2json('acer.happy.battery.snapshot')
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

    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id],
        "description": "aaa",
        "finalUserCode": "abcdefjhi",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }

    user.post(res=models.Allocate, data=post_request)
    acer = yaml2json('acer.happy.battery.snapshot')
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    action = [
        a for a in acer['components'][7]['actions'] if a['type'] == 'TestDataStorage'
    ]
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
    """Tests inserting a Live into the database and GETting it."""
    acer = file('acer.happy.battery.snapshot')
    snapshot, _ = user.post(acer, res=models.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id],
        "description": "aaa",
        "finalUserCode": "abcdefjhi",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }

    user.post(res=models.Allocate, data=post_request)
    acer = yaml2json('acer.happy.battery.snapshot')
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['lifetime'] += 1000
    acer.pop('elapsed')
    acer['licence_version'] = '1.0.0'
    live, _ = client.post(acer, res=models.Live)
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec4"
    actions = [
        a for a in acer['components'][7]['actions'] if a['type'] != 'TestDataStorage'
    ]
    acer['components'][7]['actions'] = actions
    live, _ = client.post(acer, res=models.Live)
    assert live['usageTimeAllocate'] == 1000
    tmp_snapshots = app.config['TMP_LIVES']
    shutil.rmtree(tmp_snapshots)


@pytest.mark.mvp
def test_save_live_json(app: Devicehub, user: UserClient, client: Client):
    """This test check if works the function save_snapshot_in_file"""
    acer = yaml2json('acer.happy.battery.snapshot')
    snapshot, _ = user.post(json_encode(acer), res=models.Snapshot)
    debug = 'AAA'
    acer['debug'] = debug
    device_id = snapshot['device']['id']
    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id],
        "description": "aaa",
        "finalUserCode": "abcdefjhi",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
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
    """Tests inserting a Live into the database and GETting it."""
    licences, _ = client.get('/licences/')
    licences = json.loads(licences)
    assert licences[0]['USOdyPrivacyPolicyVersion'] == '1.0.0'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_allocate(user: UserClient):
    """Tests allocate"""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    abstract = Device.query.filter_by(id=snapshot['device']['id']).one()
    device_id = abstract.binding.device.id
    devicehub_id = abstract.dhid
    post_request = {
        "transaction": "ccc",
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
    assert device['allocated'] is True
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
    """Tests allocate"""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device_id = snapshot['device']['id']
    delay = timedelta(days=30)
    future = datetime.now().replace(tzinfo=tzutc()) + delay
    post_request = {
        "transaction": "ccc",
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
    """Tests deallocate"""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    abstract = Device.query.filter_by(id=snapshot['device']['id']).one()
    device_id = abstract.binding.device.id
    devicehub_id = abstract.dhid
    post_deallocate = {
        "startTime": "2020-11-01T02:00:00+00:00",
        "transaction": "ccc",
        "devices": [device_id],
    }
    res, _ = user.post(res=models.Deallocate, data=post_deallocate, status=422)
    assert res['code'] == 422
    assert res['type'] == 'ValidationError'
    post_allocate = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "devices": [device_id],
        "description": "aaa",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }

    user.post(res=models.Allocate, data=post_allocate)
    device, _ = user.get(res=Device, item=devicehub_id)
    assert device['allocated'] is True
    deallocate, _ = user.post(res=models.Deallocate, data=post_deallocate)
    assert deallocate['startTime'] == post_deallocate['startTime']
    assert deallocate['devices'][0]['id'] == device_id
    assert deallocate['devices'][0]['allocated'] is False
    res, _ = user.post(res=models.Deallocate, data=post_deallocate, status=422)
    assert res['code'] == 422
    assert res['type'] == 'ValidationError'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_deallocate_bad_dates(user: UserClient):
    """Tests deallocate with bad date of start_time"""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device_id = snapshot['device']['id']
    delay = timedelta(days=30)
    future = datetime.now().replace(tzinfo=tzutc()) + delay
    post_deallocate = {"startTime": future, "devices": [device_id]}
    post_allocate = {
        "devices": [device_id],
        "description": "aaa",
        "startTime": "2020-11-01T02:00:00+00:00",
    }

    user.post(res=models.Allocate, data=post_allocate)
    res, _ = user.post(res=models.Deallocate, data=post_deallocate, status=422)
    assert res['code'] == 422
    assert res['type'] == 'ValidationError'


@pytest.mark.mvp
@pytest.mark.xfail(reason='Old functionality')
def test_trade_endpoint(user: UserClient, user2: UserClient):
    """Tests POST one simple Trade between 2 users of the system."""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert device['id'] == snapshot['device']['id']
    request_post = {
        'userTo': user2.user['email'],
        'price': 1.0,
        'date': "2020-12-01T02:00:00+00:00",
        'devices': [snapshot['device']['id']],
    }
    action, _ = user.post(res=models.Trade, data=request_post)

    with raises(JSONDecodeError):
        device1, _ = user.get(res=Device, item=device['id'])

    device2, _ = user2.get(res=Device, item=device['id'])
    assert device2['id'] == device['id']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_without_device(user: UserClient, user2: UserClient):
    """Test one offer with automatic confirmation and without user to"""
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)

    request_post = {
        'type': 'Trade',
        'userFromEmail': user.email,
        'userToEmail': user2.email,
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)

    trade = models.Trade.query.one()
    assert str(trade.lot.id) == lot['id']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_offer_without_to(user: UserClient):
    """Test one offer with automatic confirmation and without user to"""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device = Device.query.filter_by(id=snapshot['device']['id']).one()
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=[('id', device.id)]
    )

    # check the owner of the device
    assert device.owner.email == user.email
    for c in device.components:
        assert c.owner.email == user.email

    request_post = {
        'type': 'Trade',
        'devices': [device.id],
        'userFromEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': False,
        'code': 'MAX',
    }
    user.post(res=models.Action, data=request_post)

    trade = models.Trade.query.one()
    assert device in trade.devices
    # assert trade.confirm_transfer
    users = [ac.user for ac in trade.acceptances]
    assert trade.user_to == device.owner
    assert request_post['code'].lower() in device.owner.email
    assert device.owner.active is False
    assert device.owner.phantom is True
    assert trade.user_to in users
    assert trade.user_from in users
    assert device.owner.email != user.email
    for c in device.components:
        assert c.owner.email != user.email

    # check if the user_from is owner of the devices
    request_post = {
        'type': 'Trade',
        'devices': [device.id],
        'userFromEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': False,
        'code': 'MAX',
    }
    user.post(res=models.Action, data=request_post, status=422)
    trade = models.Trade.query.one()

    # Check if the new phantom account is reused and not duplicated
    computer = file('1-device-with-components.snapshot')
    snapshot2, _ = user.post(computer, res=models.Snapshot)
    device2 = Device.query.filter_by(id=snapshot2['device']['id']).one()
    lot2 = Lot('MyLot2')
    lot2.owner_id = user.user['id']
    lot2.devices.add(device2)
    db.session.add(lot2)
    db.session.flush()
    request_post2 = {
        'type': 'Trade',
        'devices': [device2.id],
        'userFromEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot2.id,
        'confirms': False,
        'code': 'MAX',
    }
    user.post(res=models.Action, data=request_post2)
    assert User.query.filter_by(email=device.owner.email).count() == 1


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_offer_without_from(user: UserClient, user2: UserClient):
    """Test one offer without confirmation and without user from"""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    lot = Lot('MyLot')
    lot.owner_id = user.user['id']
    device = Device.query.filter_by(id=snapshot['device']['id']).one()

    # check the owner of the device
    assert device.owner.email == user.email
    assert device.owner.email != user2.email

    lot.devices.add(device)
    db.session.add(lot)
    db.session.flush()
    request_post = {
        'type': 'Trade',
        'devices': [device.id],
        'userToEmail': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot.id,
        'confirms': False,
        'code': 'MAX',
    }
    action, _ = user2.post(res=models.Action, data=request_post, status=422)

    request_post['userToEmail'] = user.email
    action, _ = user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    phantom_user = trade.user_from
    assert request_post['code'].lower() in phantom_user.email
    assert phantom_user.active is False
    assert phantom_user.phantom is True
    # assert trade.confirm_transfer

    users = [ac.user for ac in trade.acceptances]
    assert trade.user_to in users
    assert trade.user_from in users
    assert user.email in trade.devices[0].owner.email
    assert device.owner.email != user2.email
    assert device.owner.email == user.email


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_offer_without_users(user: UserClient):
    """Test one offer with doble confirmation"""
    user2 = User(email='baz@baz.cxm', password='baz')
    user2.individuals.add(Person(name='Tommy'))
    db.session.add(user2)
    db.session.commit()
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    lot = Lot('MyLot')
    lot.owner_id = user.user['id']
    device = Device.query.filter_by(id=snapshot['device']['id']).one()
    lot.devices.add(device)
    db.session.add(lot)
    db.session.flush()
    request_post = {
        'type': 'Trade',
        'devices': [device.id],
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot.id,
        'confirms': False,
        'code': 'MAX',
    }
    action, response = user.post(res=models.Action, data=request_post, status=422)
    txt = 'you need one user from or user to for to do a trade'
    assert txt in action['message']['_schema']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_offer(user: UserClient):
    """Test one offer with doble confirmation"""
    user2 = User(email='baz@baz.cxm', password='baz')
    user2.individuals.add(Person(name='Tommy'))
    db.session.add(user2)
    db.session.commit()
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    lot = Lot('MyLot')
    lot.owner_id = user.user['id']
    device = Device.query.filter_by(id=snapshot['device']['id']).one()
    assert device.owner.email == user.email
    assert device.owner.email != user2.email
    lot.devices.add(device)
    db.session.add(lot)
    db.session.flush()
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user.email,
        'userToEmail': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot.id,
        'confirms': True,
    }

    action, _ = user.post(res=models.Action, data=request_post)
    # no there are transfer of devices
    assert device.owner.email == user.email
    assert device.owner.email != user2.email


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_offer_without_devices(user: UserClient):
    """Test one offer with doble confirmation"""
    user2 = User(email='baz@baz.cxm', password='baz')
    user2.individuals.add(Person(name='Tommy'))
    db.session.add(user2)
    db.session.commit()
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user.email,
        'userToEmail': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    # no there are transfer of devices


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_price_custom():
    computer = Desktop(
        serial_number='sn1',
        model='ml1',
        manufacturer='mr1',
        chassis=ComputerChassis.Docking,
    )
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
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_erase_physical():
    erasure = models.ErasePhysical(
        device=HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        method=enums.PhysicalErasureMethod.Disintegration,
    )
    db.session.add(erasure)
    db.session.commit()


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_endpoint_confirm(user: UserClient, user2: UserClient):
    """Check the normal creation and visualization of one confirmation trade"""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device_id = snapshot['device']['id']
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=[('id', device_id)]
    )

    request_post = {
        'type': 'Trade',
        'devices': [device_id],
        'userFromEmail': user.email,
        'userToEmail': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    assert trade.devices[0].owner.email == user.email

    request_confirm = {'type': 'Confirm', 'action': trade.id, 'devices': [device_id]}

    user2.post(res=models.Action, data=request_confirm)
    user2.post(res=models.Action, data=request_confirm, status=422)
    assert len(trade.acceptances) == 2
    assert trade.devices[0].owner.email == user2.email


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_confirm_revoke(user: UserClient, user2: UserClient):
    """Check the normal revoke of one confirmation"""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device_id = snapshot['device']['id']
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=[('id', device_id)]
    )

    request_post = {
        'type': 'Trade',
        'devices': [device_id],
        'userFromEmail': user.email,
        'userToEmail': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()
    device = trade.devices[0]

    request_confirm = {'type': 'Confirm', 'action': trade.id, 'devices': [device_id]}

    request_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device_id],
    }

    # Normal confirmation
    user2.post(res=models.Action, data=request_confirm)

    # Normal revoke
    user2.post(res=models.Action, data=request_revoke)

    # You can to do one confirmation next of one revoke
    user2.post(res=models.Action, data=request_confirm)
    assert len(trade.acceptances) == 4
    assert device.trading(trade.lot) == "TradeConfirmed"


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_usecase_confirmation(user: UserClient, user2: UserClient):
    """Example of one usecase about confirmation"""
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)
    snap3, _ = user.post(file('asus-1001pxd.snapshot'), res=models.Snapshot)
    snap4, _ = user.post(
        file('desktop-9644w8n-lenovo-0169622.snapshot'), res=models.Snapshot
    )
    snap5, _ = user.post(
        file('laptop-hp_255_g3_notebook-hewlett-packard-cnd52270fw.snapshot'),
        res=models.Snapshot,
    )
    snap6, _ = user.post(file('1-device-with-components.snapshot'), res=models.Snapshot)
    snap7, _ = user.post(file('asus-eee-1000h.snapshot.11'), res=models.Snapshot)
    snap8, _ = user.post(file('complete.export.snapshot'), res=models.Snapshot)
    snap9, _ = user.post(file('real-hp-quad-core.snapshot.11'), res=models.Snapshot)
    snap10, _ = user.post(file('david.lshw.snapshot'), res=models.Snapshot)

    devices = [
        ('id', snap1['device']['id']),
        ('id', snap2['device']['id']),
        ('id', snap3['device']['id']),
        ('id', snap4['device']['id']),
        ('id', snap5['device']['id']),
        ('id', snap6['device']['id']),
        ('id', snap7['device']['id']),
        ('id', snap8['device']['id']),
        ('id', snap9['device']['id']),
        ('id', snap10['device']['id']),
    ]
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[:7]
    )

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the SCRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()
    # l_after, _ = user.get(res=Lot, item=lot['id'])

    # the SCRAP confirms 3 of the 10 devices in its outgoing lot
    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [
            snap1['device']['id'],
            snap2['device']['id'],
            snap3['device']['id'],
        ],
    }
    assert trade.devices[0].actions[-2].t == 'Trade'
    assert trade.devices[0].actions[-1].t == 'Confirm'
    assert trade.devices[0].actions[-1].user == trade.user_to

    user2.post(res=models.Action, data=request_confirm)
    assert trade.devices[0].actions[-1].t == 'Confirm'
    assert trade.devices[0].actions[-1].user == trade.user_from
    n_actions = len(trade.devices[0].actions)

    # check validation error
    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [snap10['device']['id']],
    }

    user2.post(res=models.Action, data=request_confirm, status=422)

    # The manager add 3 device more into the lot
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[7:]
    )

    assert trade.devices[-1].actions[-2].t == 'Trade'
    assert trade.devices[-1].actions[-1].t == 'Confirm'
    assert trade.devices[-1].actions[-1].user == trade.user_to
    assert len(trade.devices[0].actions) == n_actions

    # the SCRAP confirms the rest of devices
    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [
            snap4['device']['id'],
            snap5['device']['id'],
            snap6['device']['id'],
            snap7['device']['id'],
            snap8['device']['id'],
            snap9['device']['id'],
            snap10['device']['id'],
        ],
    }

    user2.post(res=models.Action, data=request_confirm)
    assert trade.devices[-1].actions[-3].t == 'Trade'
    assert trade.devices[-1].actions[-1].t == 'Confirm'
    assert trade.devices[-1].actions[-1].user == trade.user_from
    assert len(trade.devices[0].actions) == n_actions

    # The manager remove one device of the lot and automaticaly
    # is create one revoke action
    device_10 = trade.devices[-1]
    lot, _ = user.delete(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:], status=200
    )
    assert len(trade.lot.devices) == len(trade.devices) == 10
    assert device_10.actions[-1].t == 'Revoke'

    lot, _ = user.delete(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:], status=200
    )

    assert device_10.actions[-1].t == 'Revoke'

    # the SCRAP confirms the revoke action
    request_confirm_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [snap10['device']['id']],
    }

    user2.post(res=models.Action, data=request_confirm_revoke)
    assert device_10.actions[-1].t == 'Revoke'
    assert device_10.actions[-2].t == 'Revoke'
    # assert len(trade.lot.devices) == len(trade.devices) == 9
    # assert not device_10 in trade.devices

    # check validation error
    request_confirm_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [snap9['device']['id']],
    }

    # The manager add again device_10
    # assert len(trade.devices) == 9
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:]
    )

    assert device_10.actions[-1].t == 'Confirm'
    assert device_10 in trade.devices
    assert len(trade.devices) == 10

    # the SCRAP confirms the action trade for device_10
    request_reconfirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [snap10['device']['id']],
    }
    user2.post(res=models.Action, data=request_reconfirm)
    assert device_10.actions[-1].t == 'Confirm'
    assert device_10.actions[-1].user == trade.user_from
    assert device_10.actions[-2].t == 'Confirm'
    assert device_10.actions[-2].user == trade.user_to
    assert device_10.actions[-3].t == 'Revoke'
    # assert len(device_10.actions) == 13


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_confirmRevoke(user: UserClient, user2: UserClient):
    """Example of one usecase about confirmation"""
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)
    snap3, _ = user.post(file('asus-1001pxd.snapshot'), res=models.Snapshot)
    snap4, _ = user.post(
        file('desktop-9644w8n-lenovo-0169622.snapshot'), res=models.Snapshot
    )
    snap5, _ = user.post(
        file('laptop-hp_255_g3_notebook-hewlett-packard-cnd52270fw.snapshot'),
        res=models.Snapshot,
    )
    snap6, _ = user.post(file('1-device-with-components.snapshot'), res=models.Snapshot)
    snap7, _ = user.post(file('asus-eee-1000h.snapshot.11'), res=models.Snapshot)
    snap8, _ = user.post(file('complete.export.snapshot'), res=models.Snapshot)
    snap9, _ = user.post(file('real-hp-quad-core.snapshot.11'), res=models.Snapshot)
    snap10, _ = user.post(file('david.lshw.snapshot'), res=models.Snapshot)

    devices = [
        ('id', snap1['device']['id']),
        ('id', snap2['device']['id']),
        ('id', snap3['device']['id']),
        ('id', snap4['device']['id']),
        ('id', snap5['device']['id']),
        ('id', snap6['device']['id']),
        ('id', snap7['device']['id']),
        ('id', snap8['device']['id']),
        ('id', snap9['device']['id']),
        ('id', snap10['device']['id']),
    ]
    lot, _ = user.post({}, res=Lot, item='{}/devices'.format(lot['id']), query=devices)

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    # the SCRAP confirms all of devices
    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [
            snap1['device']['id'],
            snap2['device']['id'],
            snap3['device']['id'],
            snap4['device']['id'],
            snap5['device']['id'],
            snap6['device']['id'],
            snap7['device']['id'],
            snap8['device']['id'],
            snap9['device']['id'],
            snap10['device']['id'],
        ],
    }

    user2.post(res=models.Action, data=request_confirm)
    assert trade.devices[-1].actions[-3].t == 'Trade'
    assert trade.devices[-1].actions[-1].t == 'Confirm'
    assert trade.devices[-1].actions[-1].user == trade.user_from

    # The manager remove one device of the lot and automaticaly
    # is create one revoke action
    device_10 = trade.devices[-1]
    lot, _ = user.delete(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:], status=200
    )
    # assert len(trade.lot.devices) == len(trade.devices) == 9
    # assert not device_10 in trade.devices
    assert device_10.actions[-1].t == 'Revoke'

    lot, _ = user.delete(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:], status=200
    )

    assert device_10.actions[-1].t == 'Revoke'
    # assert device_10.actions[-2].t == 'Confirm'

    # The manager add again device_10
    # assert len(trade.devices) == 9
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:]
    )

    # assert device_10.actions[-1].t == 'Confirm'
    assert device_10 in trade.devices
    assert len(trade.devices) == 10

    # TODO??? the SCRAP confirms the revoke action
    # request_confirm_revoke = {
    #     'type': 'ConfirmRevoke',
    #     'action': device_10.actions[-2].id,
    #     'devices': [snap10['device']['id']],
    # }

    # check validation error
    # user2.post(res=models.Action, data=request_confirm_revoke, status=422)

    # the SCRAP confirms the action trade for device_10
    # request_reconfirm = {
    # 'type': 'Confirm',
    # 'action': trade.id,
    # 'devices': [
    # snap10['device']['id']
    # ]
    # }
    # user2.post(res=models.Action, data=request_reconfirm)
    # assert device_10.actions[-1].t == 'Confirm'
    # assert device_10.actions[-1].user == trade.user_from
    # assert device_10.actions[-2].t == 'Confirm'
    # assert device_10.actions[-2].user == trade.user_to
    # assert device_10.actions[-3].t == 'Revoke'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case1(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)

    devices = [
        ('id', snap1['device']['id']),
        ('id', snap2['device']['id']),
    ]
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[:-1]
    )

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    lot = trade.lot
    device = trade.devices[0]

    assert device.actions[-2].t == 'Trade'
    assert device.actions[-1].t == 'Confirm'
    assert device.actions[-1].user == trade.user_to

    user.delete(
        {}, res=Lot, item='{}/devices'.format(lot.id), query=devices[:-1], status=200
    )

    assert device not in trade.lot.devices
    assert device.trading(trade.lot) == 'RevokeConfirmed'
    assert device.actions[-2].t == 'Confirm'
    assert device.actions[-1].t == 'Revoke'
    assert device.actions[-1].user == trade.user_to


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case2(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)

    devices = [
        ('id', snap1['device']['id']),
        ('id', snap2['device']['id']),
    ]
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[:-1]
    )

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:]
    )

    device1, device2 = trade.devices

    assert device1.actions[-2].t == 'Trade'
    assert device1.actions[-1].t == 'Confirm'
    assert device1.actions[-1].user == trade.user_to
    assert device2.actions[-2].t == 'Trade'
    assert device2.actions[-1].t == 'Confirm'
    assert device2.actions[-1].user == trade.user_to

    request_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device1.id, device2.id],
    }

    # Normal revoke
    user.post(res=models.Action, data=request_revoke)

    assert device1.actions[-2].t == 'Confirm'
    assert device1.actions[-1].t == 'Revoke'
    assert device1.actions[-1].user == trade.user_to
    assert device2.actions[-2].t == 'Confirm'
    assert device2.actions[-1].t == 'Revoke'
    assert device2.actions[-1].user == trade.user_to
    assert device1.trading(trade.lot) == 'RevokeConfirmed'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case3(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user2.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)

    devices = [
        ('id', snap1['device']['id']),
        ('id', snap2['device']['id']),
    ]
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[:-1]
    )

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    lot, _ = user2.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:]
    )

    device1, device2 = trade.devices

    assert device1.actions[-2].t == 'Trade'
    assert device1.actions[-1].t == 'Confirm'
    assert device1.actions[-1].user == trade.user_to
    assert device2.actions[-2].t == 'Trade'
    assert device2.actions[-1].t == 'Confirm'
    assert device2.actions[-1].user == trade.user_from

    lot, _ = user2.delete(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:], status=200
    )

    assert device2.actions[-2].t == 'Confirm'
    assert device2.actions[-1].t == 'Revoke'
    assert device2.actions[-1].user == trade.user_from
    assert device2.trading(trade.lot) == 'RevokeConfirmed'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case4(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user2.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)

    devices = [
        ('id', snap1['device']['id']),
        ('id', snap2['device']['id']),
    ]
    lot1, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[:-1]
    )

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    lot2, _ = user2.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:]
    )

    device1, device2 = trade.devices

    assert device1.actions[-2].t == 'Trade'
    assert device1.actions[-1].t == 'Confirm'
    assert device1.actions[-1].user == trade.user_to
    assert device2.actions[-2].t == 'Trade'
    assert device2.actions[-1].t == 'Confirm'
    assert device2.actions[-1].user == trade.user_from

    request_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device2.id],
    }

    # Normal revoke
    user2.post(res=models.Action, data=request_revoke)

    assert device1.actions[-2].t == 'Trade'
    assert device1.actions[-1].t == 'Confirm'
    assert device1.actions[-1].user == trade.user_to
    assert device2.actions[-2].t == 'Confirm'
    assert device2.actions[-1].t == 'Revoke'
    assert device2.actions[-1].user == trade.user_from
    assert device2.trading(trade.lot) == 'RevokeConfirmed'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case5(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)

    devices = [
        ('id', snap1['device']['id']),
        ('id', snap2['device']['id']),
    ]
    lot, _ = user.post({}, res=Lot, item='{}/devices'.format(lot['id']), query=devices)

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    device1, device2 = trade.devices

    assert device1.actions[-2].t == 'Trade'
    assert device1.actions[-1].t == 'Confirm'
    assert device1.actions[-1].user == trade.user_to
    assert device2.actions[-2].t == 'Trade'
    assert device2.actions[-1].t == 'Confirm'
    assert device2.actions[-1].user == trade.user_to

    lot, _ = user2.delete(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:], status=200
    )

    assert device2.actions[-2].t == 'Confirm'
    assert device2.actions[-1].t == 'Revoke'
    assert device2.actions[-1].user == trade.user_from

    request_confirm_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device2.id],
    }

    # Normal revoke
    user.post(res=models.Action, data=request_confirm_revoke)

    assert device2.actions[-2].t == 'Revoke'
    assert device2.actions[-1].t == 'Revoke'
    assert device2.actions[-1].user == trade.user_to
    assert device2.trading(trade.lot) == 'RevokeConfirmed'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case6(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user2.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)

    devices = [
        ('id', snap1['device']['id']),
        ('id', snap2['device']['id']),
    ]
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[:-1]
    )

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    lot, _ = user2.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:]
    )

    device1, device2 = trade.devices

    assert device1.actions[-2].t == 'Trade'
    assert device1.actions[-1].t == 'Confirm'
    assert device1.actions[-1].user == trade.user_to
    assert device2.actions[-2].t == 'Trade'
    assert device2.actions[-1].t == 'Confirm'
    assert device2.actions[-1].user == trade.user_from

    lot, _ = user.delete(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:], status=200
    )

    assert device2.actions[-2].t == 'Confirm'
    assert device2.actions[-1].t == 'Revoke'
    assert device2.actions[-1].user == trade.user_to

    request_confirm_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device2.id],
    }

    # Normal revoke
    user2.post(res=models.Action, data=request_confirm_revoke)

    assert device2.actions[-2].t == 'Revoke'
    assert device2.actions[-1].t == 'Revoke'
    assert device2.actions[-1].user == trade.user_from
    assert device2.trading(trade.lot) == 'RevokeConfirmed'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case7(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)

    devices = [('id', snap1['device']['id'])]
    lot, _ = user.post({}, res=Lot, item='{}/devices'.format(lot['id']), query=devices)

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()
    device = trade.devices[0]

    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [device.id],
    }

    # Normal revoke
    user2.post(res=models.Action, data=request_confirm)
    assert device.trading(trade.lot) == 'TradeConfirmed'

    lot, _ = user.delete(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices, status=200
    )

    request_confirm_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device.id],
    }

    user2.post(res=models.Action, data=request_confirm_revoke)

    assert device.actions[-1].t == 'Revoke'
    assert device.actions[-1].user == trade.user_from
    assert device.actions[-2].t == 'Revoke'
    assert device.actions[-2].user == trade.user_to
    assert device.actions[-3].t == 'Confirm'
    assert device.actions[-3].user == trade.user_from
    assert device.actions[-4].t == 'Confirm'
    assert device.actions[-4].user == trade.user_to
    assert device.actions[-5].t == 'Trade'
    assert device.actions[-5].author == trade.user_to
    assert device.trading(trade.lot) == 'RevokeConfirmed'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case8(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)

    devices = [('id', snap1['device']['id'])]
    lot, _ = user.post({}, res=Lot, item='{}/devices'.format(lot['id']), query=devices)

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()
    device = trade.devices[0]

    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [device.id],
    }

    # Normal revoke
    user2.post(res=models.Action, data=request_confirm)
    assert device.trading(trade.lot) == 'TradeConfirmed'

    request_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device.id],
    }

    # Normal revoke
    user.post(res=models.Action, data=request_revoke)

    request_confirm_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device.id],
    }

    user2.post(res=models.Action, data=request_confirm_revoke)

    assert device.actions[-1].t == 'Revoke'
    assert device.actions[-1].user == trade.user_from
    assert device.actions[-2].t == 'Revoke'
    assert device.actions[-2].user == trade.user_to
    assert device.actions[-3].t == 'Confirm'
    assert device.actions[-3].user == trade.user_from
    assert device.actions[-4].t == 'Confirm'
    assert device.actions[-4].user == trade.user_to
    assert device.actions[-5].t == 'Trade'
    assert device.actions[-5].author == trade.user_to
    assert device.trading(trade.lot) == 'RevokeConfirmed'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case9(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user2.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)

    devices = [('id', snap1['device']['id']), ('id', snap2['device']['id'])]
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[:-1]
    )

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    lot, _ = user2.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:]
    )

    device1, device = trade.devices

    assert device.owner == trade.user_from

    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [device.id],
    }

    # Normal revoke
    user.post(res=models.Action, data=request_confirm)
    assert device.trading(trade.lot) == 'TradeConfirmed'

    assert device.owner == trade.user_to

    lot, _ = user2.delete(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:], status=200
    )

    request_confirm_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device.id],
    }

    user.post(res=models.Action, data=request_confirm_revoke)

    assert device.owner == trade.user_from

    assert device.actions[-1].t == 'Revoke'
    assert device.actions[-1].user == trade.user_to
    assert device.actions[-2].t == 'Revoke'
    assert device.actions[-2].user == trade.user_from
    assert device.actions[-3].t == 'Confirm'
    assert device.actions[-3].user == trade.user_to
    assert device.actions[-4].t == 'Confirm'
    assert device.actions[-4].user == trade.user_from
    assert device.actions[-5].t == 'Trade'
    assert device.actions[-5].author == trade.user_to
    assert device.trading(trade.lot) == 'RevokeConfirmed'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case10(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user2.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)

    devices = [('id', snap1['device']['id']), ('id', snap2['device']['id'])]
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[:-1]
    )

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    lot, _ = user2.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:]
    )

    device1, device = trade.devices

    assert device.owner == trade.user_from
    # assert device.trading(trade.lot) == 'Confirm'

    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [device.id],
    }

    # Normal confirm
    user.post(res=models.Action, data=request_confirm)
    # assert device.trading(trade.lot) == 'TradeConfirmed'

    assert device.owner == trade.user_to

    request_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device.id],
    }

    # Normal revoke
    user2.post(res=models.Action, data=request_revoke)
    assert device.trading(trade.lot) == 'Revoke'

    request_confirm_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device.id],
    }

    user.post(res=models.Action, data=request_confirm_revoke)

    assert device.owner == trade.user_from
    assert device.actions[-1].t == 'Revoke'
    assert device.actions[-1].user == trade.user_to
    assert device.actions[-2].t == 'Revoke'
    assert device.actions[-2].user == trade.user_from
    assert device.actions[-3].t == 'Confirm'
    assert device.actions[-3].user == trade.user_to
    assert device.actions[-4].t == 'Confirm'
    assert device.actions[-4].user == trade.user_from
    assert device.actions[-5].t == 'Trade'
    assert device.actions[-5].author == trade.user_to
    assert device.trading(trade.lot) == 'RevokeConfirmed'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case11(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)

    devices = [('id', snap1['device']['id']), ('id', snap2['device']['id'])]
    lot, _ = user.post({}, res=Lot, item='{}/devices'.format(lot['id']), query=devices)

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    device1, device = trade.devices
    assert device.trading(trade.lot) == 'Confirm'

    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [device.id],
    }

    user2.post(res=models.Action, data=request_confirm)
    assert device.trading(trade.lot) == 'TradeConfirmed'

    lot, _ = user2.delete(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:], status=200
    )
    assert device.trading(trade.lot) == 'Revoke'

    request_confirm_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device.id],
    }

    user.post(res=models.Action, data=request_confirm_revoke)
    assert device.trading(trade.lot) == 'RevokeConfirmed'

    assert device.actions[-1].t == 'Revoke'
    assert device.actions[-1].user == trade.user_to
    assert device.actions[-2].t == 'Revoke'
    assert device.actions[-2].user == trade.user_from
    assert device.actions[-3].t == 'Confirm'
    assert device.actions[-3].user == trade.user_from
    assert device.actions[-4].t == 'Confirm'
    assert device.actions[-4].user == trade.user_to
    assert device.actions[-5].t == 'Trade'
    assert device.actions[-5].author == trade.user_to


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case12(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)

    devices = [('id', snap1['device']['id']), ('id', snap2['device']['id'])]
    lot, _ = user.post({}, res=Lot, item='{}/devices'.format(lot['id']), query=devices)

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    device1, device = trade.devices
    assert device.trading(trade.lot) == 'Confirm'

    # Normal confirm
    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [device.id],
    }

    user2.post(res=models.Action, data=request_confirm)
    assert device.trading(trade.lot) == 'TradeConfirmed'

    request_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device.id],
    }

    # Normal revoke
    user2.post(res=models.Action, data=request_revoke)
    assert device.trading(trade.lot) == 'Revoke'

    request_confirm_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device.id],
    }

    user.post(res=models.Action, data=request_confirm_revoke)
    assert device.trading(trade.lot) == 'RevokeConfirmed'

    assert device.actions[-1].t == 'Revoke'
    assert device.actions[-1].user == trade.user_to
    assert device.actions[-2].t == 'Revoke'
    assert device.actions[-2].user == trade.user_from
    assert device.actions[-3].t == 'Confirm'
    assert device.actions[-3].user == trade.user_from
    assert device.actions[-4].t == 'Confirm'
    assert device.actions[-4].user == trade.user_to
    assert device.actions[-5].t == 'Trade'
    assert device.actions[-5].author == trade.user_to


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case13(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user2.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)

    devices = [('id', snap1['device']['id']), ('id', snap2['device']['id'])]
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[:-1]
    )

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    lot, _ = user2.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:]
    )

    device1, device = trade.devices
    assert device1.trading(trade.lot) == 'NeedConfirmation'
    assert device.trading(trade.lot) == 'Confirm'

    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [device.id],
    }

    user.post(res=models.Action, data=request_confirm)
    assert device1.trading(trade.lot) == 'Confirm'
    assert device.trading(trade.lot) == 'TradeConfirmed'

    lot, _ = user.delete(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:], status=200
    )
    assert device1.trading(trade.lot) == 'Confirm'
    assert device.trading(trade.lot) == 'Revoke'

    request_confirm_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device.id],
    }

    user2.post(res=models.Action, data=request_confirm_revoke)
    assert device.trading(trade.lot) == 'RevokeConfirmed'

    assert device.actions[-1].t == 'Revoke'
    assert device.actions[-1].user == trade.user_from
    assert device.actions[-2].t == 'Revoke'
    assert device.actions[-2].user == trade.user_to
    assert device.actions[-3].t == 'Confirm'
    assert device.actions[-3].user == trade.user_to
    assert device.actions[-4].t == 'Confirm'
    assert device.actions[-4].user == trade.user_from
    assert device.actions[-5].t == 'Trade'
    assert device.actions[-5].author == trade.user_to


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_trade_case14(user: UserClient, user2: UserClient):
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user2.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)

    devices = [('id', snap1['device']['id']), ('id', snap2['device']['id'])]
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[:-1]
    )

    # the manager shares the temporary lot with the SCRAP as an incoming lot
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    lot, _ = user2.post(
        {}, res=Lot, item='{}/devices'.format(lot['id']), query=devices[-1:]
    )

    device1, device = trade.devices
    assert device1.trading(trade.lot) == 'NeedConfirmation'
    assert device.trading(trade.lot) == 'Confirm'

    # Normal confirm
    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [device.id],
    }

    user.post(res=models.Action, data=request_confirm)
    assert device.trading(trade.lot) == 'TradeConfirmed'

    request_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device.id],
    }

    # Normal revoke
    user.post(res=models.Action, data=request_revoke)
    assert device.trading(trade.lot) == 'Revoke'

    request_confirm_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device.id],
    }

    user2.post(res=models.Action, data=request_confirm_revoke)
    assert device.trading(trade.lot) == 'RevokeConfirmed'

    assert device.actions[-1].t == 'Revoke'
    assert device.actions[-1].user == trade.user_from
    assert device.actions[-2].t == 'Revoke'
    assert device.actions[-2].user == trade.user_to
    assert device.actions[-3].t == 'Confirm'
    assert device.actions[-3].user == trade.user_to
    assert device.actions[-4].t == 'Confirm'
    assert device.actions[-4].user == trade.user_from
    assert device.actions[-5].t == 'Trade'
    assert device.actions[-5].author == trade.user_to


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_web_erase(user: UserClient, client: Client):
    import hashlib

    from ereuse_devicehub.resources.documents import documents

    bfile = BytesIO(b'abc')
    hash3 = hashlib.sha3_256(bfile.read()).hexdigest()
    snap, _ = user.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)
    request = {
        'type': 'DataWipe',
        'devices': [snap['device']['id']],
        'name': 'borrado universal',
        'severity': 'Info',
        'description': 'nada que describir',
        'url': 'http://www.google.com/',
        'documentId': '33',
        'endTime': '2021-07-07T22:00:00.000Z',
        'filename': 'Certificado de borrado1.pdf',
        'hash': hash3,
        'success': 1,
        'software': "Blanco",
    }

    user.post(res=models.Action, data=request)
    action = models.DataWipe.query.one()
    for dev in action.devices:
        assert action in dev.actions

    assert action.document.file_hash == request['hash']

    bfile = BytesIO(b'abc')
    response, _ = client.post(
        res=documents.DocumentDef.t,
        item='stamps/',
        content_type='multipart/form-data',
        accept='text/html',
        data={'docUpload': [(bfile, 'example.csv')]},
        status=200,
    )
    assert "alert alert-info" in response
    assert "100% coincidence." in response
    assert "alert alert-danger" not in response


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_moveOnDocument(user: UserClient, user2: UserClient):
    lotIn, _ = user.post({'name': 'MyLotIn'}, res=Lot)
    lotOut, _ = user.post({'name': 'MyLotOut'}, res=Lot)
    url = (
        'http://www.ereuse.org/apapaapaapaapaapaapaapaapaapaapapaapaapaapaapaapaapaapaapaapapaapaapaapaapaapaapaapaap',
    )
    request_post1 = {
        'filename': 'test.pdf',
        'hash': 'bbbbbbbb',
        'url': url,
        'weight': 150,
        'lot': lotIn['id'],
    }
    tradedocument_from, _ = user.post(res=TradeDocument, data=request_post1)
    id_hash = 'aaaaaaaaa'
    request_post2 = {
        'filename': 'test.pdf',
        'hash': id_hash,
        'url': url,
        'weight': 0,
        'lot': lotOut['id'],
    }
    tradedocument_to, _ = user.post(res=TradeDocument, data=request_post2)

    request_trade = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lotIn['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_trade)

    description = 'This is a good description'
    request_moveOn = {
        'type': 'MoveOnDocument',
        'weight': 15,
        'container_from': tradedocument_from['id'],
        'container_to': id_hash,
        'description': description,
    }
    doc, _ = user.post(res=models.Action, data=request_moveOn)

    assert doc['weight'] == request_moveOn['weight']
    assert doc['container_from']['id'] == tradedocument_from['id']
    assert doc['container_to']['id'] == tradedocument_to['id']

    mvs = models.MoveOnDocument.query.filter().first()
    trade_from = TradeDocument.query.filter_by(id=tradedocument_from['id']).one()
    trade_to = TradeDocument.query.filter_by(id=tradedocument_to['id']).one()
    assert trade_from in mvs.documents
    assert trade_to in mvs.documents
    assert description == mvs.description
    tradedocument_to, _ = user.post(res=TradeDocument, data=request_post2)
    user.post(res=models.Action, data=request_moveOn, status=422)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_delete_devices(user: UserClient):
    """This action deactive one device and simulate than one devices is delete."""

    snap, _ = user.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)
    request = {
        'type': 'Delete',
        'devices': [snap['device']['id']],
        'name': 'borrado universal',
        'severity': 'Info',
        'description': 'duplicity of devices',
        'endTime': '2021-07-07T22:00:00.000Z',
    }

    action, _ = user.post(res=models.Action, data=request)

    # Check get one device
    user.get(res=Device, item=snap['device']['devicehubID'], status=404)
    db_device = Device.query.filter_by(id=snap['device']['id']).one()

    action_delete = sorted(db_device.actions, key=lambda x: x.created)[-1]

    assert action_delete.t == 'Delete'
    assert str(action_delete.id) == action['id']
    assert db_device.active is False

    # Check use of filter from frontend
    url = '/devices/?filter={"type":["Computer"]}'

    devices, res = user.get(url, None)
    assert len(devices['items']) == 0


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_delete_devices_check_sync(user: UserClient):
    """This action deactive one device and simulate than one devices is delete."""

    file_snap1 = file('1-device-with-components.snapshot')
    file_snap2 = file('2-device-with-components.snapshot')
    snap, _ = user.post(file_snap1, res=models.Snapshot)
    request = {
        'type': 'Delete',
        'devices': [snap['device']['id']],
        'name': 'borrado universal',
        'severity': 'Info',
        'description': 'duplicity of devices',
        'endTime': '2021-07-07T22:00:00.000Z',
    }

    action, _ = user.post(res=models.Action, data=request)

    device1 = Device.query.filter_by(id=snap['device']['id']).one()

    snap2, _ = user.post(file_snap2, res=models.Snapshot)
    request2 = {
        'type': 'Delete',
        'devices': [snap2['device']['id']],
        'name': 'borrado universal',
        'severity': 'Info',
        'description': 'duplicity of devices',
        'endTime': '2021-07-07T22:00:00.000Z',
    }

    action2, _ = user.post(res=models.Action, data=request2)

    device2 = Device.query.filter_by(id=snap2['device']['id']).one()
    # check than device2 is an other device than device1
    assert device2.id != device1.id
    # check than device2 have the components of device1
    assert (
        len(
            [
                x
                for x in device2.components
                if device1.id
                in [y.device.id for y in x.actions if hasattr(y, 'device')]
            ]
        )
        == 0
    )


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_delete_devices_permitions(user: UserClient, user2: UserClient):
    """This action deactive one device and simulate than one devices is delete."""

    file_snap = file('1-device-with-components.snapshot')
    snap, _ = user.post(file_snap, res=models.Snapshot)

    request = {
        'type': 'Delete',
        'devices': [snap['device']['id']],
        'name': 'borrado universal',
        'severity': 'Info',
        'description': 'duplicity of devices',
        'endTime': '2021-07-07T22:00:00.000Z',
    }
    action, _ = user2.post(res=models.Action, data=request, status=422)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_moveOnDocument_bug168(user: UserClient, user2: UserClient):
    """If you use one moveOnDocument in a trade Document. Next you can not drop this document."""
    lotIn, _ = user.post({'name': 'MyLotIn'}, res=Lot)
    lotOut, _ = user.post({'name': 'MyLotOut'}, res=Lot)
    url = (
        'http://www.ereuse.org/apapaapaapaapaapaapaapaapaapaapapaapaapaapaapaapaapaapaapaapapaapaapaapaapaapaapaapaap',
    )
    request_post1 = {
        'filename': 'test.pdf',
        'hash': 'bbbbbbbb',
        'url': url,
        'weight': 150,
        'lot': lotIn['id'],
    }
    tradedocument_from, _ = user.post(res=TradeDocument, data=request_post1)
    id_hash = 'aaaaaaaaa'
    request_post2 = {
        'filename': 'test.pdf',
        'hash': id_hash,
        'url': url,
        'weight': 0,
        'lot': lotOut['id'],
    }
    tradedocument_to, _ = user.post(res=TradeDocument, data=request_post2)

    request_trade = {
        'type': 'Trade',
        'devices': [],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lotIn['id'],
        'confirms': True,
    }

    user.post(res=models.Action, data=request_trade)

    description = 'This is a good description'
    request_moveOn = {
        'type': 'MoveOnDocument',
        'weight': 4,
        'container_from': tradedocument_from['id'],
        'container_to': id_hash,
        'description': description,
    }
    user.post(res=models.Action, data=request_moveOn)
    trade_document1 = TradeDocument.query.filter_by(id=tradedocument_from['id']).one()
    trade_document2 = TradeDocument.query.filter_by(id=tradedocument_to['id']).one()
    assert trade_document1.total_weight == 150.0
    assert trade_document2.total_weight == 4.0
    assert trade_document1.trading == 'Confirm'
    assert trade_document2.trading is None

    tradedocument, _ = user.delete(res=TradeDocument, item=tradedocument_to['id'])
