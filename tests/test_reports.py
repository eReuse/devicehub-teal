import csv
from io import StringIO
from pathlib import Path

import pytest
# [(t, l) for t,l in zip(test_csv[0], list_csv[0]) if t != l]

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.event.models import Snapshot
from tests.conftest import file


def test_export_endpoint(user: UserClient):
    snapshot, _ = user.post(file('basic.snapshot'), res=Snapshot)
    # device_type = snapshot['device']['type']
    csv_str, _ = user.get(res=Device, accept='text/csv')
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    test_csv = list(obj_csv)
    with Path(__file__).parent.joinpath('files').joinpath('testcsv.csv').open() as csv_file:
        obj_csv = csv.reader(csv_file)
        list_csv = list(obj_csv)
        assert test_csv == list_csv, 'Csv files are different'

def test_export_empty(user: UserClient):
    """
    Test to check works correctly exporting csv without any information
    """
    pass


def test_export_full_snaphsot(user: UserClient):
    """
    Test a export device with all fields
    :return:
    """
    pass
