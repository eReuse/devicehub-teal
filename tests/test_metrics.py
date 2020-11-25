import pytest
from datetime import timedelta
from datetime import datetime

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.resources.action import models as ma
from tests import conftest
from tests.conftest import file


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_simple_metrics(user: UserClient):
    """ Checks one standard query of metrics """
    # Insert computer
    lenovo = file('desktop-9644w8n-lenovo-0169622.snapshot')
    acer = file('acer.happy.battery.snapshot')
    user.post(lenovo, res=ma.Snapshot)
    snapshot, _ = user.post(acer, res=ma.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {"Transaction": "ccc", "name": "John", "end_users": 1,
                    "devices": [device_id], "description": "aaa",
                    "start_time": "2020-11-01T02:00:00+00:00",
                    "end_time": "2020-12-01T02:00:00+00:00"
                   }

    # Create Allocate
    user.post(res=ma.Allocate, data=post_request)
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['powerCycleCount'] += 1000
    user.post(acer, res=ma.Snapshot)

    # Create a live
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec4"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['powerCycleCount'] += 1000
    user.post(acer, res=ma.Snapshot)

    # Create an other live
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec5"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['powerCycleCount'] += 1000
    user.post(acer, res=ma.Snapshot)

    # Check metrics
    today = datetime.now()
    delta = timedelta(days=30)
    data = {"start_time": today-delta,
            "end_time": today+delta
           }
    metrics = {'allocateds': 1, 'live': 1}
    res, _ = user.get("/metrics/", query_string=data)
    assert res == metrics


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_second_hdd_metrics(user: UserClient):
    """ Checks one standard query of metrics """
    # Insert computer
    acer = file('acer.happy.battery.snapshot')
    snapshot, _ = user.post(acer, res=ma.Snapshot)
    device_id = snapshot['device']['id']
    post_request = {"Transaction": "ccc", "name": "John", "end_users": 1,
                    "devices": [device_id], "description": "aaa",
                    "start_time": "2020-11-01T02:00:00+00:00",
                    "end_time": "2020-12-01T02:00:00+00:00"
                   }

    # Create Allocate
    user.post(res=ma.Allocate, data=post_request)
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec3"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['powerCycleCount'] += 1000
    user.post(acer, res=ma.Snapshot)

    # Create a live
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec4"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd_action = [a for a in hdd['actions'] if a['type'] == 'TestDataStorage'][0]
    hdd_action['powerCycleCount'] += 1000
    user.post(acer, res=ma.Snapshot)

    # Create a second device
    acer['uuid'] = "490fb8c0-81a1-42e9-95e0-5e7db7038ec5"
    hdd = [c for c in acer['components'] if c['type'] == 'HardDrive'][0]
    hdd['serialNumber'] = 'WD-WX11A80W7440'
    user.post(acer, res=ma.Snapshot)

    # Check metrics
    today = datetime.now()
    delta = timedelta(days=30)
    data = {"start_time": today-delta,
            "end_time": today+delta
           }
    metrics = {'allocateds': 1, 'live': 2}
    res, _ = user.get("/metrics/", query_string=data)
    assert res == metrics

