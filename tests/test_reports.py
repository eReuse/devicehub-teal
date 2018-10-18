import csv

import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.event.models import Snapshot
from tests.conftest import file


def test_export_endpoint(user: UserClient):
    snapshot, _ = user.post(file('basic.snapshot'), res=Snapshot)
    # device_id = snapshot['device']['id']
    device_type = snapshot['device']['type']
    csv_list, _ = user.get(res=Device, accept='text/csv')
    read_csv = csv.reader(csv_list, delimiter=',')
    dates = []
    for row in read_csv:
        date = row[0]
        dates.append(date)

    assert dates[1] == device_type, 'Device type are not equal'
