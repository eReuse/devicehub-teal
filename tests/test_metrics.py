import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.resources.action import models as ma
from ereuse_devicehub.resources.documents import documents
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.tradedocument.models import TradeDocument
from tests import conftest
from tests.conftest import file, json_encode, yaml2json


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_simple_metrics(user: UserClient):
    """Checks one standard query of metrics"""
    # Insert computer
    lenovo = yaml2json('desktop-9644w8n-lenovo-0169622.snapshot')
    acer = yaml2json('acer.happy.battery.snapshot')
    user.post(json_encode(lenovo), res=ma.Snapshot)
    snapshot, _ = user.post(json_encode(acer), res=ma.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "finalUserCode": "abcdefjhi",
        "devices": [device_id],
        "description": "aaa",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }

    # Create Allocate
    user.post(res=ma.Allocate, data=post_request)
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['powerCycleCount'] += 1000
    acer.pop('elapsed')
    acer['licence_version'] = '1.0.0'
    user.post(acer, res=ma.Live)

    # Create a live
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec4"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['powerCycleCount'] += 1000
    user.post(acer, res=ma.Live)

    # Create an other live
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec5"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['powerCycleCount'] += 1000
    user.post(acer, res=ma.Live)

    # Check metrics
    metrics = {'allocateds': 1, 'live': 1}
    res, _ = user.get("/metrics/")
    assert res == metrics


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_second_hdd_metrics(user: UserClient):
    """Checks one standard query of metrics"""
    # Insert computer
    acer = yaml2json('acer.happy.battery.snapshot')
    snapshot, _ = user.post(json_encode(acer), res=ma.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "finalUserCode": "abcdefjhi",
        "devices": [device_id],
        "description": "aaa",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }

    # Create Allocate
    user.post(res=ma.Allocate, data=post_request)
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['powerCycleCount'] += 1000
    acer.pop('elapsed')
    acer['licence_version'] = '1.0.0'
    user.post(acer, res=ma.Live)

    # Create a live
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec4"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['powerCycleCount'] += 1000
    user.post(acer, res=ma.Live)

    # Create a second device
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec5"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd['serialNumber'] = 'WD-WX11A80W7440'
    user.post(acer, res=ma.Live)

    # Check metrics if we change the hdd we need a result of one device
    metrics = {'allocateds': 1, 'live': 1}
    res, _ = user.get("/metrics/")
    assert res == metrics


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_metrics_with_live_null(user: UserClient):
    """Checks one standard query of metrics"""
    # Insert computer
    acer = file('acer.happy.battery.snapshot')
    snapshot, _ = user.post(acer, res=ma.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {
        "transaction": "ccc",
        "name": "John",
        "endUsers": 1,
        "finalUserCode": "abcdefjhi",
        "devices": [device_id],
        "description": "aaa",
        "startTime": "2020-11-01T02:00:00+00:00",
        "endTime": "2020-12-01T02:00:00+00:00",
    }

    # Create Allocate
    user.post(res=ma.Allocate, data=post_request)

    # Check metrics if we change the hdd we need a result of one device
    metrics = {'allocateds': 1, 'live': 0}
    res, _ = user.get("/metrics/")
    assert res == metrics


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_metrics_action_status(user: UserClient, user2: UserClient):
    """Checks one standard query of metrics."""
    # Insert computer
    lenovo = yaml2json('desktop-9644w8n-lenovo-0169622.snapshot')
    snap, _ = user.post(json_encode(lenovo), res=ma.Snapshot)
    device_id = snap['device']['id']
    action = {'type': ma.Use.t, 'devices': [device_id]}
    action_use, _ = user.post(action, res=ma.Action)
    csv_str, _ = user.get(
        res=documents.DocumentDef.t,
        item='actions/',
        accept='text/csv',
        query=[('filter', {'type': ['Computer'], 'ids': [device_id]})],
    )
    head = (
        '"DHID";"Hid";"Document-Name";"Action-Type";"Action-User-LastOwner-Supplier";'
    )
    head += '"Action-User-LastOwner-Receiver";"Action-Create-By";"Trade-Confirmed";'
    head += '"Status-Created-By-Supplier-About-Reciber";"Status-Receiver";'
    head += '"Status Supplier – Created Date";"Status Receiver – Created Date";"Trade-Weight";'
    head += '"Action-Create";"Allocate-Start";"Allocate-User-Code";"Allocate-NumUsers";'
    head += '"UsageTimeAllocate";"Type";"LiveCreate";"UsageTimeHdd"\n'
    body = '"93652";"adebcc5506213fac43cd8473a9c81bcf0cadaed9cb98b2eae651e377a3533c5a";'
    body += '"";"Status";"";"foo@foo.com";"Receiver";"";"";"Use";"";"'
    assert head in csv_str
    assert body in csv_str


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_complet_metrics_with_trade(user: UserClient, user2: UserClient):
    """Checks one standard query of metrics in a trade enviroment."""
    # Insert computer
    lenovo = yaml2json('desktop-9644w8n-lenovo-0169622.snapshot')
    acer = yaml2json('acer.happy.battery.snapshot')
    snap1, _ = user.post(json_encode(lenovo), res=ma.Snapshot)
    snap2, _ = user.post(json_encode(acer), res=ma.Snapshot)
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    device1_id = snap1['device']['id']
    device2_id = snap2['device']['id']
    devices_id = [device1_id, device2_id]
    devices = [('id', device1_id), ('id', snap2['device']['id'])]
    lot, _ = user.post({}, res=Lot, item='{}/devices'.format(lot['id']), query=devices)

    action = {'type': ma.Refurbish.t, 'devices': [device1_id]}
    user.post(action, res=ma.Action)

    request_post = {
        'type': 'Trade',
        'devices': devices_id,
        'userFromEmail': user.email,
        'userToEmail': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=ma.Action, data=request_post)

    action = {'type': ma.Use.t, 'devices': [device1_id]}
    action_use, _ = user.post(action, res=ma.Action)
    csv_str, _ = user.get(
        res=documents.DocumentDef.t,
        item='actions/',
        accept='text/csv',
        query=[('filter', {'type': ['Computer'], 'ids': devices_id})],
    )

    body1_lenovo = '"93652";"adebcc5506213fac43cd8473a9c81bcf0cadaed9cb98b2eae651e377a3533c5a";"";"Trade";"foo@foo.com";'
    body1_lenovo += '"foo2@foo.com";"Supplier";"NeedConfirmation";"Use";"";'
    body2_lenovo = ';"";"0";"0";"Trade";"0";"0"\n'

    body1_acer = '"K3XW2";"55b1f6d0692d1569c7590f0aeabd1c9874a1c78b8dd3a7d481df95923a629748";"";"Trade";'
    body1_acer += (
        '"foo@foo.com";"foo2@foo.com";"Supplier";"NeedConfirmation";"";"";"";"";"0";'
    )
    body2_acer = ';"";"0";"0";"Trade";"0";"4692.0"\n'

    assert body1_lenovo in csv_str
    assert body2_lenovo in csv_str
    assert body1_acer in csv_str
    assert body2_acer in csv_str

    # User2 mark this device as Refurbish
    action = {'type': ma.Use.t, 'devices': [device1_id]}
    action_use2, _ = user2.post(action, res=ma.Action)
    csv_str, _ = user.get(
        res=documents.DocumentDef.t,
        item='actions/',
        accept='text/csv',
        query=[('filter', {'type': ['Computer'], 'ids': devices_id})],
    )

    body1_lenovo = '"93652";"adebcc5506213fac43cd8473a9c81bcf0cadaed9cb98b2eae651e377a3533c5a";"";"Trade";"foo@foo.com";'
    body1_lenovo += '"foo2@foo.com";"Supplier";"NeedConfirmation";"Use";"Use";'
    body2_lenovo = ';"";"0";"0";"Trade";"0";"0"\n'
    body2_acer = ';"";"0";"0";"Trade";"0";"4692.0"\n'

    assert body1_lenovo in csv_str
    assert body2_lenovo in csv_str
    assert body2_acer in csv_str


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_metrics_action_status_for_containers(user: UserClient, user2: UserClient):
    """Checks one standard query of metrics for a container."""
    # Insert computer
    lenovo = yaml2json('desktop-9644w8n-lenovo-0169622.snapshot')
    snap, _ = user.post(json_encode(lenovo), res=ma.Snapshot)
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    devices = [('id', snap['device']['id'])]
    lot, _ = user.post({}, res=Lot, item='{}/devices'.format(lot['id']), query=devices)
    request_post = {
        'type': 'Trade',
        'devices': [snap['device']['id']],
        'userFromEmail': user.email,
        'userToEmail': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }

    user.post(res=ma.Action, data=request_post)

    request_post = {
        'filename': 'test.pdf',
        'hash': 'bbbbbbbb',
        'url': 'http://www.ereuse.org/',
        'weight': 150,
        'lot': lot['id'],
    }
    tradedocument, _ = user.post(res=TradeDocument, data=request_post)
    action = {'type': ma.Recycling.t, 'devices': [], 'documents': [tradedocument['id']]}
    action, _ = user.post(action, res=ma.Action)
    trade = TradeDocument.query.one()

    assert str(trade.actions[-1].id) == action['id']

    # get metrics from botom in lot menu
    csv_str, _ = user.get(
        res=documents.DocumentDef.t,
        item='actions/',
        accept='text/csv',
        query=[('filter', {'type': ['Computer']}), ('lot', lot['id'])],
    )

    body1 = ';"bbbbbbbb";"test.pdf";"Trade-Container";"foo@foo.com";"foo2@foo.com";"Supplier";"False";"Recycling";"";'
    body2 = ';"";"150.0";'
    body3 = ';"";"0";"0";"Trade-Container";"0";"0"'

    assert len(csv_str.split('\n')) == 3
    assert body1 in csv_str.split('\n')[-2]
    assert body2 in csv_str.split('\n')[-2]
    assert body3 in csv_str.split('\n')[-2]

    # get metrics from botom in devices menu
    csv_str2, _ = user.get(
        res=documents.DocumentDef.t,
        item='actions/',
        accept='text/csv',
        query=[('filter', {'type': ['Computer'], 'ids': [snap['device']['id']]})],
    )

    assert len(csv_str2.split('\n')) == 4
    assert body1 in csv_str2.split('\n')[-2]
    assert body2 in csv_str2.split('\n')[-2]
    assert body3 in csv_str2.split('\n')[-2]


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_visual_metrics_for_old_owners(user: UserClient, user2: UserClient):
    """Checks if one old owner can see the metrics in a trade enviroment."""
    # Insert computer
    lenovo = yaml2json('desktop-9644w8n-lenovo-0169622.snapshot')
    snap1, _ = user.post(json_encode(lenovo), res=ma.Snapshot)
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    device_id = snap1['device']['id']
    devices = [('id', device_id)]
    lot, _ = user.post({}, res=Lot, item='{}/devices'.format(lot['id']), query=devices)
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
    trade, _ = user.post(res=ma.Action, data=request_post)

    request_confirm = {'type': 'Confirm', 'action': trade['id'], 'devices': [device_id]}
    user2.post(res=ma.Action, data=request_confirm)

    action = {'type': ma.Refurbish.t, 'devices': [device_id]}
    action_use, _ = user.post(action, res=ma.Action)
    csv_supplier, _ = user.get(
        res=documents.DocumentDef.t,
        item='actions/',
        accept='text/csv',
        query=[('filter', {'type': ['Computer'], 'ids': [device_id]})],
    )
    csv_receiver, _ = user2.get(
        res=documents.DocumentDef.t,
        item='actions/',
        accept='text/csv',
        query=[('filter', {'type': ['Computer'], 'ids': [device_id]})],
    )
    body = ';"";"0";"0";"Trade";"0";"0"\n'

    assert body in csv_receiver
    assert body in csv_supplier
    assert csv_receiver == csv_supplier


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_bug_trade_confirmed(user: UserClient, user2: UserClient):
    """When the receiber do a Trade, then the confirmation is wrong."""
    lenovo = yaml2json('desktop-9644w8n-lenovo-0169622.snapshot')
    snap1, _ = user.post(json_encode(lenovo), res=ma.Snapshot)
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    device_id = snap1['device']['id']
    devices = [('id', device_id)]
    lot, _ = user.post({}, res=Lot, item='{}/devices'.format(lot['id']), query=devices)
    request_post = {
        'type': 'Trade',
        'devices': [device_id],
        'userFromEmail': user2.email,
        'userToEmail': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirms': True,
    }
    trade, _ = user.post(res=ma.Action, data=request_post)

    csv_not_confirmed, _ = user.get(
        res=documents.DocumentDef.t,
        item='actions/',
        accept='text/csv',
        query=[('filter', {'type': ['Computer'], 'ids': [device_id]})],
    )
    request_confirm = {'type': 'Confirm', 'action': trade['id'], 'devices': [device_id]}
    user2.post(res=ma.Action, data=request_confirm)
    csv_confirmed, _ = user2.get(
        res=documents.DocumentDef.t,
        item='actions/',
        accept='text/csv',
        query=[('filter', {'type': ['Computer'], 'ids': [device_id]})],
    )

    body_not_confirmed = (
        '"Trade";"foo2@foo.com";"foo@foo.com";"Receiver";"NeedConfirmation";'
    )
    body_confirmed = '"Trade";"foo2@foo.com";"foo@foo.com";"Receiver";"TradeConfirmed";'

    assert body_not_confirmed in csv_not_confirmed
    assert body_confirmed in csv_confirmed
