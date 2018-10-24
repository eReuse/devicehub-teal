import csv
from io import StringIO
from pathlib import Path

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.event.models import Snapshot
from tests.conftest import file


def test_export_basic_snapshot(user: UserClient):
    """
    Test export device information in a csv file
    """
    snapshot, _ = user.post(file('basic.snapshot'), res=Snapshot)
    csv_str, _ = user.get(res=Device, accept='text/csv')
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    export_csv = list(obj_csv)
    # Open fixture csv and transform to list
    with Path(__file__).parent.joinpath('files').joinpath('basic.csv').open() as csv_file:
        obj_csv = csv.reader(csv_file)
        fixture_csv = list(obj_csv)

    # Pop(datetime) field d[1x][9]
    fixture_csv[1] = fixture_csv[1][:9] + fixture_csv[1][10:]
    export_csv[1] = export_csv[1][:9] + export_csv[1][10:]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert fixture_csv[1] == export_csv[1], 'Computer information are not equal'


def test_export_full_snapshot(user: UserClient):
    """
    Test a export device with all information and a lot of components
    """
    snapshot, _ = user.post(file('real-eee-1001pxd.snapshot.11'), res=Snapshot)
    csv_str, _ = user.get(res=Device, accept='text/csv')
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    export_csv = list(obj_csv)
    # Open fixture csv and transform to list
    with Path(__file__).parent.joinpath('files').joinpath('full-real-eee.csv').open() as csv_file:
        obj_csv = csv.reader(csv_file)
        fixture_csv = list(obj_csv)

    # todo one pop for each devices
    # One pop(datetime) fields d[1x][9]
    fixture_csv[1] = fixture_csv[1][:9] + fixture_csv[1][10:]
    export_csv[1] = export_csv[1][:9] + export_csv[1][10:]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert fixture_csv[1] == export_csv[1], 'Computer information are not equal'


def test_export_empty(user: UserClient):
    """
    Test to check works correctly exporting csv without any information (no snapshot)
    """
    csv_str, _ = user.get(res=Device, accept='text/csv')
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    export_csv = list(obj_csv)

    assert len(export_csv) == 0, 'Csv is not empty'


def test_export_computer_monitor(user: UserClient):
    """
    Test a export device type computer monitor
    """
    snapshot, _ = user.post(file('computer-monitor.snapshot'), res=Snapshot)
    csv_str, _ = user.get(res=Device, accept='text/csv')
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    export_csv = list(obj_csv)
    # Open fixture csv and transform to list
    with Path(__file__).parent.joinpath('files').joinpath('computer-monitor.csv').open() as csv_file:
        obj_csv = csv.reader(csv_file)
        fixture_csv = list(obj_csv)

    # One pop(datetime) fields
    fixture_csv[1] = fixture_csv[1][:8]
    export_csv[1] = export_csv[1][:8]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert fixture_csv[1] == export_csv[1], 'Component information are not equal'


def test_export_keyboard(user: UserClient):
    """
    Test a export device type keyboard
    """
    snapshot, _ = user.post(file('keyboard.snapshot'), res=Snapshot)
    csv_str, _ = user.get(res=Device, accept='text/csv')
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    export_csv = list(obj_csv)
    # Open fixture csv and transform to list
    with Path(__file__).parent.joinpath('files').joinpath('keyboard.csv').open() as csv_file:
        obj_csv = csv.reader(csv_file)
        fixture_csv = list(obj_csv)

    # One pop(datetime) fields
    fixture_csv[1] = fixture_csv[1][:8]
    export_csv[1] = export_csv[1][:8]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert fixture_csv[1] == export_csv[1], 'Component information are not equal'


def test_export_multiple_devices(user: UserClient):
    """
    Test a export multiple devices with different components and information
    """
    # todo test multiple devices
    pass
