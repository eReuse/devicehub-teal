from ereuse_devicehub.client import UserClient
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.event.models import Snapshot
from tests.conftest import file


def test_export(user: UserClient):
    snapshot, _ = user.post(file('basic.snapshot'), res=Snapshot)
    device_id = snapshot['device']['id']



    spreadsheet, _ = user.get(res=Device, accept='text/csv')
    csv.reader()
    assert
    # import csv mirar com la lib python treballa
