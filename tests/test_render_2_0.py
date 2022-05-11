import csv
import json
from io import BytesIO
from pathlib import Path

import pytest
from flask.testing import FlaskClient
from flask_wtf.csrf import generate_csrf

from ereuse_devicehub.client import UserClient, UserClientFlask
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.action.models import Snapshot
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.lot.models import Lot
from tests import conftest


def create_device(user, file_name):
    uri = '/inventory/upload-snapshot/'
    snapshot = conftest.yaml2json(file_name.split(".json")[0])
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)
    user.get(uri)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user.post(uri, data=data, content_type="multipart/form-data")

    return Snapshot.query.one()


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_login(user: UserClient, app: Devicehub):
    """Checks a simple login"""

    client = FlaskClient(app, use_cookies=True)

    body, status, headers = client.get('/login/')
    body = next(body).decode("utf-8")
    assert status == '200 OK'
    assert "Login to Your Account" in body

    data = {
        'email': user.email,
        'password': 'foo',
        'remember': False,
        'csrf_token': generate_csrf(),
    }
    body, status, headers = client.post('/login/', data=data, follow_redirects=True)

    body = next(body).decode("utf-8")
    assert status == '200 OK'
    assert "Login to Your Account" not in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_profile(user3: UserClientFlask):
    body, status = user3.get('/profile/')

    assert status == '200 OK'
    assert "Profile" in body
    assert user3.email in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_inventory(user3: UserClientFlask):
    body, status = user3.get('/inventory/device/')

    assert status == '200 OK'
    assert "Unassigned" in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_lot(user3: UserClientFlask):
    body, status = user3.get('/inventory/lot/add/')

    lot_name = "lot1"
    assert status == '200 OK'
    assert "Add a new lot" in body
    assert lot_name not in body

    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    body, status = user3.post('/inventory/lot/add/', data=data)

    assert status == '200 OK'
    assert lot_name in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_del_lot(user3: UserClientFlask):
    body, status = user3.get('/inventory/lot/add/')

    lot_name = "lot1"
    assert status == '200 OK'
    assert "Add a new lot" in body
    assert lot_name not in body

    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    body, status = user3.post('/inventory/lot/add/', data=data)

    assert status == '200 OK'
    assert lot_name in body

    lot = Lot.query.filter_by(name=lot_name).one()
    uri = '/inventory/lot/{id}/del/'.format(id=lot.id)
    body, status = user3.get(uri)
    assert lot_name not in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_update_lot(user3: UserClientFlask):
    user3.get('/inventory/lot/add/')

    # Add lot
    data = {
        'name': "lot1",
        'csrf_token': generate_csrf(),
    }
    user3.post('/inventory/lot/add/', data=data)

    data = {
        'name': "lot2",
        'csrf_token': generate_csrf(),
    }

    lot = Lot.query.one()
    uri = '/inventory/lot/{uuid}/'.format(uuid=lot.id)
    body, status = user3.post(uri, data=data)

    assert status == '200 OK'
    assert "lot2" in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_upload_snapshot(user3: UserClientFlask):
    uri = '/inventory/upload-snapshot/'
    file_name = 'real-eee-1001pxd.snapshot.12.json'
    body, status = user3.get(uri)

    assert status == '200 OK'
    assert "Select a Snapshot file" in body

    snapshot = conftest.yaml2json(file_name.split(".json")[0])
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    body, status = user3.post(uri, data=data, content_type="multipart/form-data")

    txt = f"{file_name}: Ok"
    assert status == '200 OK'
    assert txt in body
    db_snapthot = Snapshot.query.one()
    dev = db_snapthot.device
    assert str(db_snapthot.uuid) == snapshot['uuid']
    assert dev.type == 'Laptop'
    assert dev.serial_number == 'b8oaas048285'
    assert len(dev.actions) == 12
    assert len(dev.components) == 9


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_inventory_with_device(user3: UserClientFlask):
    db_snapthot = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    body, status = user3.get('/inventory/device/')

    assert status == '200 OK'
    assert "Unassigned" in body
    assert db_snapthot.device.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_inventory_filter(user3: UserClientFlask):
    db_snapthot = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')

    csrf = generate_csrf()
    body, status = user3.get(f'/inventory/device/?filter=Laptop&csrf_token={csrf}')

    assert status == '200 OK'
    assert "Unassigned" in body
    assert db_snapthot.device.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_export_devices(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    uri = "/inventory/export/devices/?ids={id}".format(id=snap.device.devicehub_id)

    body, status = user3.get(uri)
    assert status == '200 OK'

    export_csv = [line.split(";") for line in body.split("\n")]

    with Path(__file__).parent.joinpath('files').joinpath(
        'export_devices.csv'
    ).open() as csv_file:
        obj_csv = csv.reader(csv_file, delimiter=';', quotechar='"')
        fixture_csv = list(obj_csv)

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert (
        fixture_csv[1][:19] == export_csv[1][:19]
    ), 'Computer information are not equal'
    assert fixture_csv[1][20] == export_csv[1][20], 'Computer information are not equal'
    assert (
        fixture_csv[1][22:82] == export_csv[1][22:82]
    ), 'Computer information are not equal'
    assert fixture_csv[1][83] == export_csv[1][83], 'Computer information are not equal'
    assert (
        fixture_csv[1][86:] == export_csv[1][86:]
    ), 'Computer information are not equal'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_export_metrics(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    uri = "/inventory/export/metrics/?ids={id}".format(id=snap.device.devicehub_id)

    body, status = user3.get(uri)
    assert status == '200 OK'
    assert body == ''


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_export_certificates(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    uri = "/inventory/export/certificates/?ids={id}".format(id=snap.device.devicehub_id)

    body, status = user3.get(uri, decode=False)
    body = str(next(body))
    assert status == '200 OK'
    assert "PDF-1.5" in body
    assert 'hts54322' in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_labels(user3: UserClientFlask):
    body, status = user3.get('/labels/')

    assert status == '200 OK'
    assert "Unique Identifiers Management" in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_tag(user3: UserClientFlask):
    uri = '/labels/add/'
    body, status = user3.get(uri)

    assert status == '200 OK'
    assert "Add a new Unique Identifier" in body

    data = {
        'code': "tag1",
        'csrf_token': generate_csrf(),
    }
    body, status = user3.post(uri, data=data)

    assert status == '200 OK'
    assert "tag1" in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_label_details(user3: UserClientFlask):
    uri = '/labels/add/'
    user3.get(uri)

    data = {
        'code': "tag1",
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data)

    body, status = user3.get('/labels/tag1/')
    assert "tag1" in body
    assert "Print Label" in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_link_tag_to_device(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/labels/add/'
    user3.get(uri)

    data = {
        'code': "tag1",
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data)

    body, status = user3.get('/inventory/device/')
    assert "tag1" in body

    data = {
        'tag': "tag1",
        'device': dev.id,
        'csrf_token': generate_csrf(),
    }

    uri = '/inventory/tag/devices/add/'
    user3.post(uri, data=data)
    assert len(list(dev.tags)) == 2
    tags = [tag.id for tag in dev.tags]
    assert "tag1" in tags


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_unlink_tag_to_device(user3: UserClientFlask):
    # create device
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device

    # create tag
    uri = '/labels/add/'
    user3.get(uri)

    data = {
        'code': "tag1",
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data)

    # link tag to device
    data = {
        'tag': "tag1",
        'device': dev.id,
        'csrf_token': generate_csrf(),
    }

    uri = '/inventory/tag/devices/add/'
    user3.post(uri, data=data)

    # unlink tag to device
    uri = '/inventory/tag/devices/{id}/del/'.format(id=dev.id)
    user3.get(uri)

    data = {
        'code': "tag1",
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data)

    data = {
        'tag': "tag1",
        'csrf_token': generate_csrf(),
    }

    user3.post(uri, data=data)
    assert len(list(dev.tags)) == 1
    tag = list(dev.tags)[0]
    assert not tag.id == "tag1"


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_print_labels(user3: UserClientFlask):
    # create device
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device

    # create tag
    uri = '/labels/add/'
    user3.get(uri)

    data = {
        'code': "tag1",
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data)

    # link tag to device
    data = {
        'tag': "tag1",
        'device': dev.id,
        'csrf_token': generate_csrf(),
    }

    uri = '/inventory/tag/devices/add/'
    user3.post(uri, data=data)

    assert len(list(dev.tags)) == 2

    uri = '/labels/print'
    data = {
        'devices': "{}".format(dev.id),
        'csrf_token': generate_csrf(),
    }
    body, status = user3.post(uri, data=data)

    assert status == '200 OK'
    path = "/inventory/device/{}/".format(dev.devicehub_id)
    assert path in body
    assert "tag1" not in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_monitor(user3: UserClientFlask):
    uri = '/inventory/device/add/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "New Device" in body

    data = {
        'csrf_token': generate_csrf(),
        'type': "Monitor",
        'serial_number': "AAAAB",
        'model': "LC27T55",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Device &#34;Monitor&#34; created successfully!' in body
    dev = Device.query.one()
    assert dev.type == 'Monitor'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_filter_monitor(user3: UserClientFlask):
    uri = '/inventory/device/add/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Monitor",
        'serial_number': "AAAAB",
        'model': "LC27T55",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
    }
    user3.post(uri, data=data)
    csrf = generate_csrf()

    uri = f'/inventory/device/?filter=Monitor&csrf_token={csrf}'
    body, status = user3.get(uri)

    assert status == '200 OK'
    dev = Device.query.one()
    assert dev.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_recycling(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    # fail request
    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert dev.actions[-1].type == 'EreusePrice'
    assert 'Action Allocate error!' in body

    # good request
    data = {
        'csrf_token': generate_csrf(),
        'type': "Recycling",
        'severity': "Info",
        'devices': "{}".format(dev.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.actions[-1].type == 'Recycling'
    assert 'Action &#34;Recycling&#34; created successfully!' in body
    assert dev.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_error_without_devices(user3: UserClientFlask):
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Recycling",
        'severity': "Info",
        'devices': "",
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Action Recycling error!' in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_use(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Use",
        'severity': "Info",
        'devices': "{}".format(dev.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.actions[-1].type == 'Use'
    assert 'Action &#34;Use&#34; created successfully!' in body
    assert dev.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_refurbish(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Refurbish",
        'severity': "Info",
        'devices': "{}".format(dev.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.actions[-1].type == 'Refurbish'
    assert 'Action &#34;Refurbish&#34; created successfully!' in body
    assert dev.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_management(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Management",
        'severity': "Info",
        'devices': "{}".format(dev.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.actions[-1].type == 'Management'
    assert 'Action &#34;Management&#34; created successfully!' in body
    assert dev.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_allocate(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.id),
        'start_time': '2000-01-01',
        'end_time': '2000-06-01',
        'end_users': 2,
    }

    uri = '/inventory/action/allocate/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.actions[-1].type == 'Allocate'
    assert 'Action &#34;Allocate&#34; created successfully!' in body
    assert dev.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_allocate_error_required(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Trade",
        'severity': "Info",
        'devices': "{}".format(dev.id),
    }

    uri = '/inventory/action/allocate/add/'
    body, status = user3.post(uri, data=data)
    assert dev.actions[-1].type != 'Allocate'

    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.id),
    }

    uri = '/inventory/action/allocate/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Action Allocate error' in body
    assert 'Not a valid date value.' in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_allocate_error_dates(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.id),
        'start_time': '2000-06-01',
        'end_time': '2000-01-01',
        'end_users': 2,
    }

    uri = '/inventory/action/allocate/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Action Allocate error' in body
    assert 'The action cannot finish before it starts.' in body
    assert dev.actions[-1].type != 'Allocate'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_deallocate(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.id),
        'start_time': '2000-01-01',
        'end_time': '2000-06-01',
        'end_users': 2,
    }

    uri = '/inventory/action/allocate/add/'

    user3.post(uri, data=data)
    assert dev.actions[-1].type == 'Allocate'

    data = {
        'csrf_token': generate_csrf(),
        'type': "Deallocate",
        'severity': "Info",
        'devices': "{}".format(dev.id),
        'start_time': '2000-01-01',
        'end_time': '2000-06-01',
        'end_users': 2,
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.actions[-1].type == 'Deallocate'
    assert 'Action &#34;Deallocate&#34; created successfully!' in body
    assert dev.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_toprepare(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "ToPrepare",
        'severity': "Info",
        'devices': "{}".format(dev.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.actions[-1].type == 'ToPrepare'
    assert 'Action &#34;ToPrepare&#34; created successfully!' in body
    assert dev.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_prepare(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Prepare",
        'severity': "Info",
        'devices': "{}".format(dev.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.actions[-1].type == 'Prepare'
    assert 'Action &#34;Prepare&#34; created successfully!' in body
    assert dev.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_torepair(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "ToRepair",
        'severity': "Info",
        'devices': "{}".format(dev.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.actions[-1].type == 'ToRepair'
    assert 'Action &#34;ToRepair&#34; created successfully!' in body
    assert dev.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_ready(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Ready",
        'severity': "Info",
        'devices': "{}".format(dev.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.actions[-1].type == 'Ready'
    assert 'Action &#34;Ready&#34; created successfully!' in body
    assert dev.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_datawipe(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    b_file = b'1234567890'
    file_name = "my_file.doc"
    file_upload = (BytesIO(b_file), file_name)

    data = {
        'csrf_token': generate_csrf(),
        'type': "DataWipe",
        'severity': "Info",
        'devices': "{}".format(dev.id),
        'document-file_name': file_upload,
    }

    uri = '/inventory/action/datawipe/add/'
    body, status = user3.post(uri, data=data, content_type="multipart/form-data")
    assert status == '200 OK'
    assert dev.actions[-1].type == 'DataWipe'
    assert 'Action &#34;DataWipe&#34; created successfully!' in body
    assert dev.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb_settings(user3: UserClientFlask):
    uri = '/workbench/settings/'
    body, status = user3.get(uri)

    assert status == '200 OK'
    assert "Download your settings for Workbench" in body
    assert "Workbench Settings" in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb_settings_register(user3: UserClientFlask):
    uri = '/workbench/settings/?opt=register'
    body, status = user3.get(uri)

    assert status == '200 OK'
    assert "WB_BENCHMARK = False" in body
    assert "WB_ERASE = \n" in body
    assert "WB_ERASE_STEPS = 0" in body
    assert "WB_ERASE_LEADING_ZEROS = False" in body
