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
from ereuse_devicehub.resources.lot.models import Lot
from tests import conftest


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
def test_inventory(user3: UserClientFlask):
    body, status = user3.get('/inventory/device/')

    assert status == '200 OK'
    assert "Unassgined" in body


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
    # import pdb; pdb.set_trace()
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
    uri = '/inventory/upload-snapshot/'
    file_name = 'real-eee-1001pxd.snapshot.12.json'
    snapshot = conftest.yaml2json(file_name.split(".json")[0])
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)
    user3.get(uri)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")

    body, status = user3.get('/inventory/device/')

    assert status == '200 OK'
    assert "Unassgined" in body
    db_snapthot = Snapshot.query.one()
    assert db_snapthot.device.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_inventory_filter(user3: UserClientFlask):
    uri = '/inventory/upload-snapshot/'
    file_name = 'real-eee-1001pxd.snapshot.12.json'
    snapshot = conftest.yaml2json(file_name.split(".json")[0])
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)
    user3.get(uri)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")

    csrf = generate_csrf()
    body, status = user3.get(f'/inventory/device/?filter=Laptop&csrf_token={csrf}')

    assert status == '200 OK'
    assert "Unassgined" in body
    db_snapthot = Snapshot.query.one()
    assert db_snapthot.device.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_export_devices(user3: UserClientFlask):
    uri = '/inventory/upload-snapshot/'
    file_name = 'real-eee-1001pxd.snapshot.12.json'
    snapshot = conftest.yaml2json(file_name.split(".json")[0])
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)
    user3.get(uri)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")

    snap = Snapshot.query.one()
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
