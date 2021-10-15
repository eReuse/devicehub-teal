import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.resources.action import models as ma
from ereuse_devicehub.resources.documents import documents
from tests import conftest
from tests.conftest import file, yaml2json, json_encode


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_simple_metrics(user: UserClient):
    """ Checks one standard query of metrics """
    # Insert computer
    lenovo = yaml2json('desktop-9644w8n-lenovo-0169622.snapshot')
    acer = yaml2json('acer.happy.battery.snapshot')
    user.post(json_encode(lenovo), res=ma.Snapshot)
    snapshot, _ = user.post(json_encode(acer), res=ma.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "finalUserCode": "abcdefjhi",
                    "devices": [device_id], "description": "aaa",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
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
    """ Checks one standard query of metrics """
    # Insert computer
    acer = yaml2json('acer.happy.battery.snapshot')
    snapshot, _ = user.post(json_encode(acer), res=ma.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "finalUserCode": "abcdefjhi",
                    "devices": [device_id], "description": "aaa",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
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
    """ Checks one standard query of metrics """
    # Insert computer
    acer = file('acer.happy.battery.snapshot')
    snapshot, _ = user.post(acer, res=ma.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {"transaction": "ccc", "name": "John", "endUsers": 1,
                    "finalUserCode": "abcdefjhi",
                    "devices": [device_id], "description": "aaa",
                    "startTime": "2020-11-01T02:00:00+00:00",
                    "endTime": "2020-12-01T02:00:00+00:00"
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
    """ Checks one standard query of metrics """
    # Insert computer
    lenovo = yaml2json('desktop-9644w8n-lenovo-0169622.snapshot')
    snap, _ = user.post(json_encode(lenovo), res=ma.Snapshot)
    action = {'type': ma.Use.t, 'devices': [snap['device']['id']]}
    action_use, _ = user.post(action, res=ma.Action)
    # res, _ = user.get("/metrics/")
    csv_str, _ = user.get(res=documents.DocumentDef.t,
                          item='actions/',
                          accept='text/csv',
                          query=[('filter', {'type': ['Computer']})])
    # import pdb; pdb.set_trace()
    head = 'DHID;Hid;Document-Name;Action-Type;Action-User-LastOwner-Supplier;Action-User-LastOwner-Receiver;Action-Create-By;Trade-Confirmed;Status-Supplier;Status-Receiver;Status Supplier – Created Date;Status Receiver – Created Date;Trade-Weight;Allocate-Start;Allocate-User-Code;Allocate-NumUsers;UsageTimeAllocate;Type;LiveCreate;UsageTimeHdd\n'
    body = '93652;desktop-lenovo-9644w8n-0169622-00:1a:6b:5e:7f:10;;Status;;foo@foo.com;Receiver;;;Use;;'
    assert head in csv_str
    assert body in csv_str


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_complet_metrics(user: UserClient, user2: UserClient):
    """ Checks one standard query of metrics """
    # Insert computer
    lenovo = yaml2json('desktop-9644w8n-lenovo-0169622.snapshot')
    acer = yaml2json('acer.happy.battery.snapshot')
    snap1, _ = user.post(json_encode(lenovo), res=ma.Snapshot)
    snap2, _ = user.post(json_encode(acer), res=ma.Snapshot)
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    devices = [('id', snap1['device']['id']),
               ('id', snap2['device']['id'])
              ]
    lot, _ = user.post({},
                       res=Lot,
                       item='{}/devices'.format(lot['id']),
                       query=devices)
    # import pdb; pdb.set_trace()
    # request_post = {
        # 'type': 'Trade',
        # 'devices': [span1['device']['id'], snap2['device']['id']],
        # 'userFromEmail': user2.email,
        # 'userToEmail': user.email,
        # 'price': 10,
        # 'date': "2020-12-01T02:00:00+00:00",
        # 'lot': lot['id'],
        # 'confirms': True,
    # }

    # user.post(res=models.Action, data=request_post)

    # ==============================
    # Check metrics
    metrics = {'allocateds': 1, 'live': 1}
    res, _ = user.get("/metrics/")
    assert res == metrics
