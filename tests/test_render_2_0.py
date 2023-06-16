import datetime
import json
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
from flask import g
from flask.testing import FlaskClient
from flask_wtf.csrf import generate_csrf

from ereuse_devicehub.client import UserClient, UserClientFlask
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.action.models import Snapshot
from ereuse_devicehub.resources.device.models import Device, Placeholder
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.user.models import User
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
    assert "Sign in" in body

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
    assert len(dev.actions) == 10
    assert len(dev.components) == 9


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_upload_snapshot_to_lot(user3: UserClientFlask):
    user3.get('/inventory/lot/add/')
    lot_name = 'lot1'
    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    user3.post('/inventory/lot/add/', data=data)
    lot = Lot.query.filter_by(name=lot_name).one()

    lot_id = lot.id
    uri = f'/inventory/lot/{lot_id}/upload-snapshot/'
    file_name = 'real-eee-1001pxd.snapshot.12.json'
    user3.get(uri)

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
    assert dev not in lot.devices
    assert dev.binding.device in lot.devices

    uri = f'/inventory/lot/{lot_id}/device/'
    body, status = user3.get(uri)
    assert dev.binding.device.devicehub_id in body
    assert dev.binding.phid in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_inventory_with_device(user3: UserClientFlask):
    db_snapthot = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    body, status = user3.get('/inventory/device/')

    assert status == '200 OK'
    assert "Unassigned" in body
    assert db_snapthot.device.binding.device.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_inventory_filter(user3: UserClientFlask):
    db_snapthot = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')

    csrf = generate_csrf()
    body, status = user3.get(f'/inventory/device/?filter=Laptop&csrf_token={csrf}')

    assert status == '200 OK'
    assert "Unassigned" in body
    assert db_snapthot.device.binding.device.devicehub_id in body


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
        fixture_csv = [line.split(";") for line in csv_file.read().split("\n")]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert (
        fixture_csv[1][:33] == export_csv[1][:33]
    ), 'Computer information are not equal'
    assert fixture_csv[1][34] == export_csv[1][34], 'Computer information are not equal'
    assert (
        fixture_csv[1][36:97] == export_csv[1][36:97]
    ), 'Computer information are not equal'

    assert fixture_csv[1][98] == export_csv[1][98], 'Computer information are not equal'
    assert (
        fixture_csv[1][102:] == export_csv[1][102:]
    ), 'Computer information are not equal'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_export_obada_standard(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    uri = "/inventory/export/obada_standard/?ids={id}".format(
        id=snap.device.devicehub_id
    )

    body, status = user3.get(uri)
    assert status == '200 OK'

    export_csv = [line.split(";") for line in body.split("\n")]

    with Path(__file__).parent.joinpath('files').joinpath(
        'export_obada_standard.csv'
    ).open() as csv_file:
        fixture_csv = [line.split(";") for line in csv_file.read().split("\n")]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert fixture_csv[1] == export_csv[1], 'body are not equal'


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
    assert 'e2024242cv86mm'.upper() in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_export_actions_erasure(user3: UserClientFlask):
    snap = create_device(user3, 'erase-sectors-2-hdd.snapshot')
    ids = [str(ac.id) for ac in snap.actions if ac.type == 'EraseBasic']
    ids = ",".join(ids)
    uri = "/inventory/export/actions_erasures/?ids={id}".format(id=ids)

    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "WD-WCAV27984668" in body
    assert "WD-WCAV29008961" in body


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
    assert "Print Label" in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_link_tag_to_device(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device.binding.device
    uri = '/labels/add/'
    user3.get(uri)

    data = {
        'code': "tag1",
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data)

    body, status = user3.get('/inventory/device/{}/'.format(dev.dhid))
    assert "tag1" in body

    data = {
        'tag': "tag1",
        'device': dev.dhid,
        'csrf_token': generate_csrf(),
    }

    uri = '/inventory/tag/devices/{}/add/'.format(dev.dhid)
    user3.post(uri, data=data)
    assert len(list(dev.tags)) == 1
    tags = [tag.id for tag in dev.tags]
    assert "tag1" in tags


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_unlink_tag_to_device(user3: UserClientFlask):
    # create device
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device.binding.device

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
    assert len(list(dev.tags)) == 0


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_print_labels(user3: UserClientFlask):
    # create device
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device.binding.device

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

    uri = '/inventory/tag/devices/{}/add/'.format(dev.dhid)
    user3.post(uri, data=data)

    assert len(list(dev.tags)) == 1

    uri = '/labels/print'
    data = {
        'devices': "{}".format(dev.id),
        'csrf_token': generate_csrf(),
    }
    body, status = user3.post(uri, data=data)

    assert status == '200 OK'
    path = "/devices/{}".format(dev.dhid)
    assert path in body
    assert "tag1" in body


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
        'id_device_supplier': "b2",
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'

    dev = Device.query.one()
    typ = dev.type
    dhid = dev.dhid
    phid = dev.phid()

    assert typ == 'Monitor'
    assert dev.placeholder.id_device_supplier == "b2"
    assert dev.hid == 'monitor-samsung-lc27t55-aaaab'
    assert phid == '1'
    assert dhid == '93652'

    txt = f'Device &#34;{typ}&#34; placeholder with PHID {phid} and DHID {dhid} '
    txt += 'created successfully'
    assert txt in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_update_monitor(user3: UserClientFlask):
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
        'id_device_supplier': "b2",
        'pallet': "l34",
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'

    dev = Device.query.one()
    typ = dev.type
    dhid = dev.dhid
    phid = dev.phid()

    assert typ == 'Monitor'
    assert dev.placeholder.id_device_supplier == "b2"
    assert dev.hid == 'monitor-samsung-lc27t55-aaaab'
    assert phid == '1'
    assert dhid == '93652'
    assert dev.model == 'lc27t55'
    assert dev.depth == 0.1
    assert dev.placeholder.pallet == "l34"

    txt = f'Device &#34;{typ}&#34; placeholder with PHID {phid} and DHID {dhid} '
    txt += 'created successfully'
    assert txt in body

    data = {
        'csrf_token': generate_csrf(),
        'type': "Monitor",
        'serial_number': "AAAAB",
        'model': "LCD 43 b",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.2,
        'id_device_supplier': "b3",
        'pallet': "l20",
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    # assert 'Error, exist one Placeholder device with this PHID' in body
    dev = Device.query.all()[0]
    assert Device.query.count() == 2
    assert dev.type == 'Monitor'
    assert dev.placeholder.id_device_supplier == "b2"
    assert dev.hid == 'monitor-samsung-lc27t55-aaaab'
    assert dev.placeholder.phid == '1'
    assert dev.model == 'lc27t55'
    assert dev.depth == 0.1
    assert dev.placeholder.pallet == "l34"


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_2_monitor(user3: UserClientFlask):
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
        'id_device_supplier': "b1",
        'pallet': "l34",
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'

    dev = Device.query.one()
    typ = dev.type
    dhid = dev.dhid
    phid = dev.phid()

    assert typ == 'Monitor'
    assert dev.placeholder.id_device_supplier == "b1"
    assert dev.hid == 'monitor-samsung-lc27t55-aaaab'
    assert phid == '1'
    assert dhid == '93652'
    assert dev.model == 'lc27t55'
    assert dev.placeholder.pallet == "l34"

    txt = f'Device &#34;{typ}&#34; placeholder with PHID {phid} and DHID {dhid} '
    txt += 'created successfully'
    assert txt in body

    data = {
        'csrf_token': generate_csrf(),
        'type': "Monitor",
        'serial_number': "AAAAB",
        'model': "LCD 43 b",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.2,
        'id_device_supplier': "b2",
        'pallet': "l20",
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'

    dev = Device.query.all()[-1]
    typ = dev.type
    dhid = dev.dhid
    phid = dev.phid()

    assert typ == 'Monitor'
    assert dev.placeholder.id_device_supplier == "b2"
    assert dev.hid == 'monitor-samsung-lcd_43_b-aaaab'
    assert phid == '2'
    assert dev.model == 'lcd 43 b'
    assert dev.placeholder.pallet == "l20"

    assert dhid == 'E39W3'

    txt = f'Device &#34;{typ}&#34; placeholder with PHID {phid} and DHID {dhid} '
    txt += 'created successfully'
    assert txt in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_laptop(user3: UserClientFlask):
    uri = '/inventory/device/add/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "New Device" in body

    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'serial_number': "AAAAB",
        'model': "LC27T55",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "b2",
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'

    dev = Device.query.one()
    typ = dev.type
    dhid = dev.dhid
    phid = dev.phid()

    assert typ == 'Laptop'
    assert dev.placeholder.id_device_supplier == "b2"
    assert (
        dev.chid == '274f05421e4d394c5b3cd10266fed6f0500029b104b5db3521689bda589e3150'
    )
    assert phid == '1'
    assert dhid == '93652'

    txt = f'Device &#34;{typ}&#34; placeholder with PHID {phid} and DHID {dhid} '
    txt += 'created successfully'
    assert txt in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_with_ammount_laptops(user3: UserClientFlask):
    uri = '/inventory/device/add/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "New Device" in body

    num = 3

    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'amount': num,
        'serial_number': "AAAAB",
        'model': "LC27T55",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "b2",
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert f'{num} placeholders Device &#34;Laptop&#34; created successfully.' in body

    for dev in Device.query.all():
        assert dev.type == 'Laptop'
        assert dev.placeholder.id_device_supplier is None
        assert dev.hid == 'laptop-samsung-lc27t55-'
        assert (
            dev.chid
            == 'ff8e7794d33ed22046b8d94b8bba4d8d1507f0fee535150835cac28faabbcda1'
        )
        assert dev.placeholder.phid in [str(x) for x in range(1, num + 1)]
    assert Device.query.count() == num


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
        'devices': "{}".format(dev.binding.device.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert dev.actions[-1].type == 'Snapshot'
    assert 'Action Allocate error!' in body

    # good request
    data = {
        'csrf_token': generate_csrf(),
        'type': "Recycling",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.binding.device.actions[-1].type == 'Recycling'
    assert 'Action &#34;Recycling&#34; created successfully!' in body
    assert dev.binding.device.devicehub_id in body


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
        'devices': "{}".format(dev.binding.device.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.binding.device.actions[-1].type == 'Use'
    assert 'Action &#34;Use&#34; created successfully!' in body
    assert dev.binding.device.devicehub_id in body


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
        'devices': "{}".format(dev.binding.device.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.binding.device.actions[-1].type == 'Refurbish'
    assert 'Action &#34;Refurbish&#34; created successfully!' in body
    assert dev.binding.device.devicehub_id in body


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
        'devices': "{}".format(dev.binding.device.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.binding.device.actions[-1].type == 'Management'
    assert 'Action &#34;Management&#34; created successfully!' in body
    assert dev.binding.device.devicehub_id in body


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
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-01-01',
        'end_time': '2000-06-01',
        'end_users': 2,
    }

    uri = '/inventory/action/allocate/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.binding.device.actions[-1].type == 'Allocate'
    assert 'Action &#34;Allocate&#34; created successfully!' in body
    assert dev.binding.device.devicehub_id in body


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
        'devices': "{}".format(dev.binding.device.id),
    }

    uri = '/inventory/action/allocate/add/'
    body, status = user3.post(uri, data=data)
    assert 'Allocate' not in [x.type for x in dev.binding.device.actions]

    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
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
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-06-01',
        'end_time': '2000-01-01',
        'end_users': 2,
    }

    uri = '/inventory/action/allocate/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Action Allocate error' in body
    assert 'The action cannot finish before it starts.' in body
    assert 'Allocate' not in [x.type for x in dev.binding.device.actions]


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_allocate_error_future_dates(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)
    start_time = (datetime.datetime.now() + datetime.timedelta(1)).strftime('%Y-%m-%d')
    end_time = (datetime.datetime.now() + datetime.timedelta(10)).strftime('%Y-%m-%d')

    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': start_time,
        'end_time': end_time,
        'end_users': 2,
    }

    uri = '/inventory/action/allocate/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Action Allocate error' in body
    assert 'Not a valid date value.!' in body
    assert 'Allocate' not in [x.type for x in dev.binding.device.actions]


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
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-01-01',
        'end_time': '2000-06-01',
        'end_users': 2,
    }

    uri = '/inventory/action/allocate/add/'

    user3.post(uri, data=data)
    assert dev.binding.device.allocated_status.type == 'Allocate'

    data = {
        'csrf_token': generate_csrf(),
        'type': "Deallocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-01-01',
        'end_time': '2000-06-01',
        'end_users': 2,
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.binding.device.allocated_status.type == 'Deallocate'
    assert 'Action &#34;Deallocate&#34; created successfully!' in body
    assert dev.binding.device.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_deallocate_error(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-05-01',
        'end_time': '2000-06-01',
        'end_users': 2,
    }

    uri = '/inventory/action/allocate/add/'

    user3.post(uri, data=data)
    assert dev.binding.device.allocated_status.type == 'Allocate'

    data = {
        'csrf_token': generate_csrf(),
        'type': "Deallocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-01-01',
        'end_time': '2000-02-01',
        'end_users': 2,
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.binding.device.allocated_status.type != 'Deallocate'
    assert 'Action Deallocate error!' in body
    assert 'Error, some of this devices are actually deallocate' in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_allocate_deallocate_error(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-01-01',
        'end_time': '2000-01-01',
        'end_users': 2,
    }

    uri = '/inventory/action/allocate/add/'

    user3.post(uri, data=data)
    assert dev.binding.device.allocated_status.type == 'Allocate'
    assert len(dev.binding.device.actions) == 1

    data = {
        'csrf_token': generate_csrf(),
        'type': "Deallocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-02-01',
        'end_time': '2000-02-01',
        'end_users': 2,
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.binding.device.allocated_status.type == 'Deallocate'
    assert len(dev.binding.device.actions) == 2

    # is not possible to do an allocate between an allocate and an deallocate
    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-01-15',
        'end_time': '2000-01-15',
        'end_users': 2,
    }

    user3.post(uri, data=data)
    assert dev.binding.device.allocated_status.type == 'Deallocate'

    data = {
        'csrf_token': generate_csrf(),
        'type': "Deallocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-01-15',
        'end_time': '2000-01-15',
        'end_users': 2,
    }

    user3.post(uri, data=data)
    assert len(dev.binding.device.actions) == 2


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_allocate_deallocate_error2(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-01-10',
        'end_users': 2,
    }

    uri = '/inventory/action/allocate/add/'

    user3.post(uri, data=data)
    assert len(dev.binding.device.actions) == 1

    data = {
        'csrf_token': generate_csrf(),
        'type': "Deallocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-01-20',
        'end_users': 2,
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert len(dev.binding.device.actions) == 2

    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-02-10',
        'end_users': 2,
    }

    uri = '/inventory/action/allocate/add/'

    user3.post(uri, data=data)
    assert len(dev.binding.device.actions) == 3

    data = {
        'csrf_token': generate_csrf(),
        'type': "Deallocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-02-20',
        'end_users': 2,
    }
    user3.post(uri, data=data)
    assert len(dev.binding.device.actions) == 4

    data = {
        'csrf_token': generate_csrf(),
        'type': "Allocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-01-25',
        'end_users': 2,
    }
    user3.post(uri, data=data)
    assert len(dev.binding.device.actions) == 5

    data = {
        'csrf_token': generate_csrf(),
        'type': "Deallocate",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'start_time': '2000-01-27',
        'end_users': 2,
    }
    user3.post(uri, data=data)
    assert len(dev.binding.device.actions) == 6


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
        'devices': "{}".format(dev.binding.device.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.binding.device.actions[-1].type == 'ToPrepare'
    assert 'Action &#34;ToPrepare&#34; created successfully!' in body
    assert dev.binding.device.devicehub_id in body


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
        'devices': "{}".format(dev.binding.device.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.binding.device.actions[-1].type == 'Prepare'
    assert 'Action &#34;Prepare&#34; created successfully!' in body
    assert dev.binding.device.devicehub_id in body


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
        'devices': "{}".format(dev.binding.device.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.binding.device.actions[-1].type == 'ToRepair'
    assert 'Action &#34;ToRepair&#34; created successfully!' in body
    assert dev.binding.device.devicehub_id in body


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
        'devices': "{}".format(dev.binding.device.id),
    }

    uri = '/inventory/action/add/'
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert dev.binding.device.actions[-1].type == 'Ready'
    assert 'Action &#34;Ready&#34; created successfully!' in body
    assert dev.binding.device.devicehub_id in body


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
        'devices': "{}".format(dev.binding.device.id),
        'document-file_name': file_upload,
    }

    uri = '/inventory/action/datawipe/add/'
    body, status = user3.post(uri, data=data, content_type="multipart/form-data")
    assert status == '200 OK'
    assert dev.binding.device.actions[-1].type == 'DataWipe'
    assert 'Action &#34;DataWipe&#34; created successfully!' in body
    assert dev.binding.device.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_action_erasedatawipe(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    b_file = b'1234567890'
    file_name = "my_file.doc"
    file_upload = (BytesIO(b_file), file_name)

    data = {
        'csrf_token': generate_csrf(),
        'type': "EraseDataWipe",
        'severity': "Info",
        'devices': "{}".format(dev.binding.device.id),
        'document-file_name': file_upload,
    }

    uri = '/inventory/action/datawipe/add/'
    body, status = user3.post(uri, data=data, content_type="multipart/form-data")
    assert status == '200 OK'
    assert dev.binding.device.actions[-1].type == 'EraseDataWipe'
    assert 'Action &#34;EraseDataWipe&#34; created successfully!' in body
    assert dev.binding.device.devicehub_id in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb_settings(user3: UserClientFlask):
    uri = '/workbench/'
    body, status = user3.get(uri)

    assert status == '200 OK'
    assert "Please download the ISO file and the settings file of the" in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb_settings_register(user3: UserClientFlask):
    uri = '/workbench/?opt=register'
    body, status = user3.get(uri)

    assert status == '200 OK'
    assert "TOKEN = " in body
    assert "URL = https://" in body
    assert "/api/inventory/" in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_create_transfer(user3: UserClientFlask):
    user3.get('/inventory/lot/add/')
    lot_name = 'lot1'
    lot_name2 = 'lot2'
    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    user3.post('/inventory/lot/add/', data=data)
    lot = Lot.query.filter_by(name=lot_name).one()

    lot_id = lot.id
    uri = f'/inventory/lot/{lot_id}/transfer/incoming/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert 'Add new transfer' in body
    assert 'Code' in body
    assert 'Description' in body
    assert 'Save' in body

    data = {'csrf_token': generate_csrf(), 'code': 'AAA', 'lot_name': lot_name2}

    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Transfer created successfully!' in body
    assert 'Delete Lot' in body
    assert 'Incoming Lot' in body
    assert lot_name2 in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_edit_transfer(user3: UserClientFlask):
    # create lot
    user3.get('/inventory/lot/add/')
    lot_name = 'lot1'
    lot_name2 = 'lot2'
    lot_name3 = 'lot3'
    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    user3.post('/inventory/lot/add/', data=data)
    lot = Lot.query.filter_by(name=lot_name).one()

    # render temporary lot
    lot_id = lot.id
    uri = f'/inventory/lot/{lot_id}/device/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert 'Transfer (<span class="text-success">Open</span>)' not in body
    assert '<i class="bi bi-trash"></i> Delete Lot' in body

    # create new incoming lot
    uri = f'/inventory/lot/{lot_id}/transfer/incoming/'
    data = {'csrf_token': generate_csrf(), 'code': 'AAA', 'lot_name': lot_name2}
    body, status = user3.post(uri, data=data)
    assert 'Transfer (<span class="text-success">Open</span>)' in body
    assert '<i class="bi bi-trash"></i> Delete Lot' in body
    lot = Lot.query.filter()[1]
    assert lot.transfer is not None
    assert lot_name2 in body

    # edit transfer with errors
    lot_id = lot.id
    uri = f'/inventory/lot/{lot_id}/transfer/'
    data = {
        'csrf_token': generate_csrf(),
        'code': 'AAA',
        'description': 'one one one',
        'lot_name': lot_name3,
        'date': datetime.datetime.now().date() + datetime.timedelta(15),
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Transfer updated error!' in body
    assert 'one one one' not in body
    assert '<i class="bi bi-trash"></i> Delete Lot' in body
    assert 'Transfer (<span class="text-success">Open</span>)' in body

    # # edit transfer successfully
    data = {
        'csrf_token': generate_csrf(),
        'code': 'AAA',
        'description': 'one one one',
        'lot_name': lot_name3,
        'date': datetime.datetime.now().date() - datetime.timedelta(15),
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Transfer updated successfully!' in body
    assert 'one one one' in body
    assert '<i class="bi bi-trash"></i> Delete Lot' not in body
    assert 'Transfer (<span class="text-danger">Closed</span>)' in body
    assert lot_name3 in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_edit_deliverynote(user3: UserClientFlask):
    # create lot
    user3.get('/inventory/lot/add/')
    lot_name = 'lot1'
    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    user3.post('/inventory/lot/add/', data=data)
    lot = Lot.query.filter_by(name=lot_name).one()
    lot_id = lot.id

    # create new incoming lot
    uri = f'/inventory/lot/{lot_id}/transfer/incoming/'
    data = {'csrf_token': generate_csrf(), 'code': 'AAA', 'lot_name': lot_name}
    user3.post(uri, data=data)
    lot = Lot.query.filter()[1]
    lot_id = lot.id

    # edit delivery with errors
    uri = f'/inventory/lot/{lot_id}/deliverynote/'
    data = {
        'csrf_token': generate_csrf(),
        'number': 'AAA',
        'units': 10,
        'weight': 50,
        'date': datetime.datetime.now().date() + datetime.timedelta(15),
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Delivery Note updated error!' in body

    # # edit transfer successfully
    data['date'] = datetime.datetime.now().date() - datetime.timedelta(15)
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Delivery Note updated successfully!' in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_edit_receivernote(user3: UserClientFlask):
    # create lot
    user3.get('/inventory/lot/add/')
    lot_name = 'lot1'
    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    user3.post('/inventory/lot/add/', data=data)
    lot = Lot.query.filter_by(name=lot_name).one()
    lot_id = lot.id

    # create new incoming lot
    uri = f'/inventory/lot/{lot_id}/transfer/incoming/'
    data = {'csrf_token': generate_csrf(), 'code': 'AAA', 'lot_name': lot_name}
    user3.post(uri, data=data)
    lot = Lot.query.filter()[1]
    lot_id = lot.id

    # edit delivery with errors
    uri = f'/inventory/lot/{lot_id}/receivernote/'
    data = {
        'csrf_token': generate_csrf(),
        'number': 'AAA',
        'units': 10,
        'weight': 50,
        'date': datetime.datetime.now().date() + datetime.timedelta(15),
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Receiver Note updated error!' in body

    # # edit transfer successfully
    data['date'] = datetime.datetime.now().date() - datetime.timedelta(15)
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Receiver Note updated successfully!' in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_edit_notes_with_closed_transfer(user3: UserClientFlask):
    # create lot
    user3.get('/inventory/lot/add/')
    lot_name = 'lot1'
    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    user3.post('/inventory/lot/add/', data=data)
    lot = Lot.query.filter_by(name=lot_name).one()
    lot_id = lot.id

    # create new incoming lot
    uri = f'/inventory/lot/{lot_id}/transfer/incoming/'
    data = {'csrf_token': generate_csrf(), 'code': 'AAA', 'lot_name': lot_name}
    user3.post(uri, data=data)
    lot = Lot.query.filter()[1]
    lot_id = lot.id

    # edit transfer adding date
    uri = f'/inventory/lot/{lot_id}/transfer/'
    data['date'] = datetime.datetime.now().date() - datetime.timedelta(15)
    user3.post(uri, data=data)
    assert lot.transfer.closed is True

    # edit delivery with errors
    uri = f'/inventory/lot/{lot_id}/deliverynote/'
    data = {
        'csrf_token': generate_csrf(),
        'number': 'AAA',
        'units': 10,
        'weight': 50,
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Delivery Note updated error!' in body

    # edit receiver with errors
    uri = f'/inventory/lot/{lot_id}/receivernote/'
    data = {
        'csrf_token': generate_csrf(),
        'number': 'AAA',
        'units': 10,
        'weight': 50,
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Receiver Note updated error!' in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_export_devices_lots(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    user3.get('/inventory/lot/add/')
    lot_name = 'lot1'
    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    user3.post('/inventory/lot/add/', data=data)
    lot = Lot.query.filter_by(name=lot_name).one()

    device = snap.device
    g.user = User.query.one()
    device.lots.update({lot})
    db.session.commit()

    uri = "/inventory/export/devices_lots/?ids={id}".format(id=snap.device.devicehub_id)

    body, status = user3.get(uri)
    assert status == '200 OK'

    export_csv = [line.split(";") for line in body.split("\n")]

    with Path(__file__).parent.joinpath('files').joinpath(
        'devices_lots.csv'
    ).open() as csv_file:
        fixture_csv = [line.split(";") for line in csv_file.read().split("\n")]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert fixture_csv[1][2:] == export_csv[1][2:], 'Computer information are not equal'
    UUID(export_csv[1][1].replace('"', ''))


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_export_lots(user3: UserClientFlask):
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    user3.get('/inventory/lot/add/')
    lot_name = 'lot1'
    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    user3.post('/inventory/lot/add/', data=data)
    lot = Lot.query.filter_by(name=lot_name).one()

    device = snap.device
    g.user = User.query.one()
    device.lots.update({lot})
    db.session.commit()

    uri = "/inventory/export/lots/"

    body, status = user3.get(uri)
    assert status == '200 OK'

    export_csv = [line.split(";") for line in body.split("\n")]

    with Path(__file__).parent.joinpath('files').joinpath(
        'lots.csv'
    ).open() as csv_file:
        fixture_csv = [line.split(";") for line in csv_file.read().split("\n")]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert fixture_csv[1][1:] == export_csv[1][1:], 'Computer information are not equal'
    UUID(export_csv[1][0].replace('"', ''))


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_export_snapshot_json(user3: UserClientFlask):
    file_name = 'real-eee-1001pxd.snapshot.13.json'
    snap = create_device(user3, file_name)

    snapshot = conftest.yaml2json(file_name.split(".json")[0])
    snapshot = json.dumps(snapshot)

    uri = "/inventory/export/snapshot/?id={}".format(snap.uuid)
    body, status = user3.get(uri)
    assert status == '200 OK'
    body = json.loads(body)
    snapshot = json.loads(snapshot)
    assert body['device'] == snapshot['device']
    assert body['components'] == snapshot['components']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_placeholder_excel(user3: UserClientFlask):
    uri = '/inventory/upload-placeholder/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "Upload Placeholder" in body

    file_path = Path(__file__).parent.joinpath('files').joinpath('placeholder_test.xls')
    with open(file_path, 'rb') as excel:
        data = {
            'csrf_token': generate_csrf(),
            'type': "Laptop",
            'placeholder_file': excel,
        }
        user3.post(uri, data=data, content_type="multipart/form-data")
    assert Device.query.count() == 3
    dev = Device.query.first()
    chid = 'f28ae12ffd513f5ed8fb6714a344a2326c48a7196fb140435065ab96ffda1a71'
    assert dev.chid == chid
    assert dev.placeholder.phid == '1'
    assert dev.placeholder.info == 'Good conditions'
    assert dev.placeholder.pallet == '24A'
    assert dev.placeholder.id_device_supplier == 'TTT'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_placeholder_csv(user3: UserClientFlask):

    uri = '/inventory/upload-placeholder/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "Upload Placeholder" in body

    file_path = Path(__file__).parent.joinpath('files').joinpath('placeholder_test.csv')
    with open(file_path, 'rb') as excel:
        data = {
            'csrf_token': generate_csrf(),
            'type': "Laptop",
            'placeholder_file': excel,
        }
        user3.post(uri, data=data, content_type="multipart/form-data")
    assert Device.query.count() == 3
    dev = Device.query.first()
    chid = 'f28ae12ffd513f5ed8fb6714a344a2326c48a7196fb140435065ab96ffda1a71'
    assert dev.chid == chid
    assert dev.placeholder.phid == '1'
    assert dev.placeholder.info == 'Good conditions'
    assert dev.placeholder.pallet == '24A'
    assert dev.placeholder.id_device_supplier == 'TTT'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_placeholder_ods(user3: UserClientFlask):

    uri = '/inventory/upload-placeholder/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "Upload Placeholder" in body

    file_path = Path(__file__).parent.joinpath('files').joinpath('placeholder_test.ods')
    with open(file_path, 'rb') as excel:
        data = {
            'csrf_token': generate_csrf(),
            'type': "Laptop",
            'placeholder_file': excel,
        }
        user3.post(uri, data=data, content_type="multipart/form-data")
    assert Device.query.count() == 3
    dev = Device.query.first()
    chid = 'f28ae12ffd513f5ed8fb6714a344a2326c48a7196fb140435065ab96ffda1a71'
    assert dev.chid == chid
    assert dev.placeholder.phid == '1'
    assert dev.placeholder.info == 'Good conditions'
    assert dev.placeholder.pallet == '24A'
    assert dev.placeholder.id_device_supplier == 'TTT'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_placeholder_office_open_xml(user3: UserClientFlask):

    uri = '/inventory/upload-placeholder/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "Upload Placeholder" in body

    file_path = (
        Path(__file__).parent.joinpath('files').joinpath('placeholder_test.xlsx')
    )
    with open(file_path, 'rb') as excel:
        data = {
            'csrf_token': generate_csrf(),
            'type': "Laptop",
            'placeholder_file': excel,
        }
        user3.post(uri, data=data, content_type="multipart/form-data")
    assert Device.query.count() == 3
    dev = Device.query.first()
    chid = 'f28ae12ffd513f5ed8fb6714a344a2326c48a7196fb140435065ab96ffda1a71'
    assert dev.chid == chid
    assert dev.placeholder.phid == '1'
    assert dev.placeholder.info == 'Good conditions'
    assert dev.placeholder.pallet == '24A'
    assert dev.placeholder.id_device_supplier == 'TTT'
    assert dev.placeholder.id_device_internal == 'AA'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_edit_laptop(user3: UserClientFlask):
    uri = '/inventory/device/add/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "New Device" in body

    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'serial_number': "AAAAB",
        'model': "LC27T55",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "b2",
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'

    dev = Device.query.one()
    typ = dev.type
    dhid = dev.dhid
    phid = dev.phid()

    assert typ == 'Laptop'
    assert dev.placeholder.id_device_supplier == "b2"
    chid = '274f05421e4d394c5b3cd10266fed6f0500029b104b5db3521689bda589e3150'
    assert dev.chid == chid
    assert dev.serial_number == 'aaaab'
    assert dev.model == 'lc27t55'
    assert phid == '1'
    assert dhid == '93652'

    txt = f'Device &#34;{typ}&#34; placeholder with PHID {phid} and DHID {dhid} '
    txt += 'created successfully'
    assert txt in body

    uri = '/inventory/device/edit/{}/'.format(dev.devicehub_id)
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "Edit Device" in body

    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'serial_number': "AAAAC",
        'model': "LC27T56",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "a2",
    }
    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Device &#34;Laptop&#34; edited successfully!' in body
    dev = Device.query.one()
    assert dev.type == 'Laptop'
    assert dev.chid == chid
    assert dev.placeholder.phid == '1'
    assert dev.placeholder.id_device_supplier == 'a2'
    assert dev.serial_number == 'aaaac'
    assert dev.model == 'lc27t56'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_placeholder_log_manual_new(user3: UserClientFlask):
    uri = '/inventory/device/add/'
    user3.get(uri)
    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'phid': 'ace',
        'serial_number': "AAAAB",
        'model': "LC27T55",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "b2",
    }
    user3.post(uri, data=data)

    uri = '/inventory/placeholder-logs/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "Placeholder Logs" in body
    assert "Web form" in body
    assert "ace" in body
    assert "New device" in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_placeholder_log_manual_edit(user3: UserClientFlask):
    uri = '/inventory/device/add/'
    user3.get(uri)
    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'serial_number': "AAAAB",
        'part_number': "AAAAB",
        'model': "LC27T55",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "b2",
        'id_device_internal': "b2i",
    }
    user3.post(uri, data=data)
    dev = Device.query.one()
    plz = Placeholder.query.first()
    assert plz.id_device_supplier == "b2"
    assert plz.id_device_internal == "b2i"

    uri = '/inventory/device/edit/{}/'.format(dev.devicehub_id)
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'serial_number': "AAAAC",
        'model': "LC27T56",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "a2",
        'id_device_internal': "a2i",
    }
    user3.post(uri, data=data)
    plz = Placeholder.query.first()
    assert plz.id_device_supplier == "a2"
    assert plz.id_device_internal == "a2i"

    uri = '/inventory/placeholder-logs/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "Placeholder Logs" in body
    assert "Update" in body
    assert "Web form" in body
    assert "1" in body
    assert dev.devicehub_id in body
    assert "✓" in body
    assert "CSV" not in body
    assert "Excel" not in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_placeholder_log_excel_new(user3: UserClientFlask):

    uri = '/inventory/upload-placeholder/'
    body, status = user3.get(uri)

    file_path = Path(__file__).parent.joinpath('files').joinpath('placeholder_test.xls')
    with open(file_path, 'rb') as excel:
        data = {
            'csrf_token': generate_csrf(),
            'type': "Laptop",
            'placeholder_file': excel,
        }
        user3.post(uri, data=data, content_type="multipart/form-data")
    dev = Device.query.first()
    assert dev.placeholder.phid == '1'

    uri = '/inventory/placeholder-logs/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "Placeholder Logs" in body
    assert dev.placeholder.phid in body
    assert dev.devicehub_id in body
    assert "Web form" not in body
    assert "New device" in body
    assert "✓" in body
    assert "CSV" not in body
    assert "Excel" in body
    assert "placeholder_test.xls" in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_placeholder_log_excel_update(user3: UserClientFlask):

    uri = '/inventory/upload-placeholder/'
    body, status = user3.get(uri)

    file_path = Path(__file__).parent.joinpath('files').joinpath('placeholder_test.xls')
    with open(file_path, 'rb') as excel:
        data = {
            'csrf_token': generate_csrf(),
            'type': "Laptop",
            'placeholder_file': excel,
        }
        user3.post(uri, data=data, content_type="multipart/form-data")

    file_path = Path(__file__).parent.joinpath('files').joinpath('placeholder_test.csv')
    with open(file_path, 'rb') as excel:
        data = {
            'csrf_token': generate_csrf(),
            'type': "Laptop",
            'placeholder_file': excel,
        }
        user3.post(uri, data=data, content_type="multipart/form-data")

    dev = Device.query.first()
    assert dev.placeholder.phid == '1'

    uri = '/inventory/placeholder-logs/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "Placeholder Logs" in body
    assert dev.placeholder.phid in body
    assert dev.devicehub_id in body
    assert "Web form" not in body
    assert "New device" in body
    assert "✓" in body
    assert "CSV" in body
    assert "Excel" in body
    assert "placeholder_test.xls" in body
    assert "placeholder_test.csv" in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_placeholder_excel_from_lot(user3: UserClientFlask):
    user3.get('/inventory/lot/add/')
    lot_name = 'lot1'
    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    user3.post('/inventory/lot/add/', data=data)
    lot = Lot.query.filter_by(name=lot_name).one()
    lot_id = lot.id

    uri = f'/inventory/lot/{lot_id}/upload-placeholder/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "Upload Placeholder" in body

    file_path = Path(__file__).parent.joinpath('files').joinpath('placeholder_test.xls')
    with open(file_path, 'rb') as excel:
        data = {
            'csrf_token': generate_csrf(),
            'type': "Laptop",
            'placeholder_file': excel,
        }
        user3.post(uri, data=data, content_type="multipart/form-data")
    assert Device.query.count() == 3
    dev = Device.query.first()
    chid = 'f28ae12ffd513f5ed8fb6714a344a2326c48a7196fb140435065ab96ffda1a71'
    assert dev.chid == chid
    assert dev.placeholder.phid == '1'
    assert dev.placeholder.info == 'Good conditions'
    assert dev.placeholder.pallet == '24A'
    assert dev.placeholder.id_device_supplier == 'TTT'
    assert len(lot.devices) == 3


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_new_placeholder_from_lot(user3: UserClientFlask):
    user3.get('/inventory/lot/add/')
    lot_name = 'lot1'
    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    user3.post('/inventory/lot/add/', data=data)
    lot = Lot.query.filter_by(name=lot_name).one()
    assert len(lot.devices) == 0
    lot_id = lot.id

    uri = f'/inventory/lot/{lot_id}/device/add/'

    user3.get(uri)
    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'serial_number': "AAAAB",
        'model': "LC27T55",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "b2",
    }
    user3.post(uri, data=data)
    dev = Device.query.one()
    chid = '274f05421e4d394c5b3cd10266fed6f0500029b104b5db3521689bda589e3150'
    assert dev.chid == chid
    assert dev.placeholder.phid == '1'
    assert len(lot.devices) == 1


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_manual_binding(user3: UserClientFlask):
    # create placeholder manual
    uri = '/inventory/device/add/'

    user3.get(uri)
    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'serial_number': "AAAAB",
        'model': "LC27T55",
        'manufacturer': "Samsung",
        'generation': 1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "b2",
    }
    user3.post(uri, data=data)
    dev = Device.query.one()
    chid = '274f05421e4d394c5b3cd10266fed6f0500029b104b5db3521689bda589e3150'
    assert dev.chid == chid
    assert dev.placeholder.phid == '1'
    assert dev.placeholder.is_abstract is False

    # add device from wb
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev_wb = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    assert dev_wb.binding.is_abstract is True
    assert (
        dev_wb.chid
        == '83cb9066430a8ea7def04af61d521d6517193a486c02ea3bc914c9eaeb2b718b'
    )
    assert dev_wb.binding.phid == '11'
    old_placeholder = dev_wb.binding

    # page binding
    dhid = dev_wb.dhid
    uri = f'/inventory/binding/{dhid}/1/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert 'sid' in body
    assert 'Confirm' in body

    phid_real = dev.placeholder.phid
    phid_abstract = dev_wb.binding.phid
    dhid_real = dev.dhid
    dhid_abstract = dev_wb.dhid

    # action binding
    body, status = user3.post(uri, data={})
    assert status == '200 OK'
    txt = f"Device placeholder with PHID: {phid_real} and DHID: {dhid_real} "
    txt += f"bind successfully with device snapshot PHID: {phid_abstract} DHID: {dhid_abstract}."
    assert txt in body

    # check new structure
    assert dev_wb.binding.phid == '1'
    assert dev_wb.binding.device == dev
    assert dev_wb.phid() == dev.phid()
    assert dev_wb.is_abstract() == dev.is_abstract() == 'Twin'
    # assert dev_wb.
    assert Placeholder.query.filter_by(id=old_placeholder.id).first() is None
    assert Device.query.filter_by(id=old_placeholder.device.id).first() is None

    body_real, status = user3.get(f'/devices/{dhid_real}')
    body_abstract, status = user3.get(f'/devices/{dhid_abstract}')
    assert body_real == body_abstract


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_edit_and_binding(user3: UserClientFlask):
    uri = '/inventory/device/add/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'serial_number': "AAAAB",
        'model': "LC27T55",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "b2",
    }
    user3.post(uri, data=data)

    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev_wb = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    uri = '/inventory/device/edit/{}/'.format(dev_wb.binding.device.devicehub_id)
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert "Edit Device" in body

    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'serial_number': "AAAAC",
        'model': "LC27T56",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "a2",
    }
    assert dev_wb.binding.is_abstract is True
    user3.post(uri, data=data)
    assert dev_wb.binding.is_abstract is True


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_unbinding(user3: UserClientFlask):
    # create placeholder manual
    uri = '/inventory/device/add/'

    user3.get(uri)
    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'serial_number': "AAAAB",
        'model': "LC27T55",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "b2",
    }
    user3.post(uri, data=data)
    dev = Device.query.one()

    # add device from wb
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev_wb = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    old_placeholder = dev_wb.binding
    old_phid = old_placeholder.phid
    old_dhid = dev_wb.dhid

    # page binding
    dhid = dev_wb.dhid
    uri = f'/inventory/binding/{dhid}/1/'
    user3.get(uri)

    # action binding
    assert Placeholder.query.count() == 11
    assert dev.placeholder.binding is None
    user3.post(uri, data={})
    assert dev.placeholder.binding == dev_wb
    assert Placeholder.query.count() == 1

    dhid = dev.dhid
    # action unbinding
    uri = '/inventory/unbinding/1/'
    body, status = user3.post(uri, data={})
    assert status == '200 OK'
    txt = f'Device with PHID:&#34;1&#34; and DHID: {dhid} unbind successfully!'
    assert txt in body
    # assert 'Device &#34;sid&#34; unbind successfully!' in body

    # check new structure

    assert dev.placeholder.binding is None
    assert dev_wb.binding.phid == old_phid
    assert dev_wb.dhid == old_dhid
    assert old_placeholder.device.model == dev_wb.binding.device.model
    assert old_placeholder.device != dev_wb.binding.device
    assert Placeholder.query.filter_by(id=old_placeholder.id).first() is None
    assert Device.query.filter_by(id=old_placeholder.device.id).first() is None
    assert Placeholder.query.filter_by(id=dev_wb.binding.id).first()
    assert Device.query.filter_by(id=dev_wb.binding.device.id).first()
    assert Device.query.filter_by(id=dev.id).first()
    assert Placeholder.query.filter_by(id=dev.placeholder.id).first()
    assert Placeholder.query.count() == 11


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_unbindingnot_used(user3: UserClientFlask):
    # add device from wb
    snap = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    dev_wb = snap.device
    uri = '/inventory/device/'
    user3.get(uri)

    old_placeholder = dev_wb.binding

    # action unbinding
    uri = '/inventory/unbinding/{}/'.format(dev_wb.binding.phid)
    body, status = user3.post(uri, data={})
    assert status == '200 OK'

    # check new structure
    assert dev_wb.binding == old_placeholder
    assert Placeholder.query.filter_by(id=old_placeholder.id).first()
    assert Device.query.filter_by(id=old_placeholder.device.id).first()
    assert Device.query.filter_by(id=dev_wb.id).first()


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_upload_snapshot_smartphone(user3: UserClientFlask):
    uri = '/inventory/upload-snapshot/'
    file_name = 'smartphone.snapshot.json'
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
    assert dev.type == 'Smartphone'
    assert dev.serial_number == 'abcdef'
    assert dev.binding.device.serial_number == 'abcdef'
    assert dev.placeholder is None
    assert len(dev.actions) == 2


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_list_erasures(user3: UserClientFlask):
    from flask import current_app as app

    app.config['SCHEMA'] = 'test'
    uri = '/inventory/upload-snapshot/'
    file_name = 'erase-sectors-2-hdd.snapshot.yaml'
    body, status = user3.get(uri)

    assert status == '200 OK'
    assert "Select a Snapshot file" in body

    snapshot = conftest.yaml2json(file_name.split(".yaml")[0])
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }

    user3.post(uri, data=data, content_type="multipart/form-data")

    uri = '/inventory/device/erasure/'
    body, status = user3.get(uri)

    txt = "WD-WCAV27984668"
    assert status == '200 OK'
    assert txt in body

    uri = '/inventory/device/erasure/1/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert txt not in body

    dev = Device.query.first()
    dev.binding.kangaroo = True
    db.session.commit()

    body, status = user3.get(uri)
    assert status == '200 OK'
    assert txt in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_bug_3821_binding(user3: UserClientFlask):
    uri = '/inventory/device/add/'
    user3.get(uri)

    data = {
        'csrf_token': generate_csrf(),
        'type': "Laptop",
        'phid': 'sid',
        'serial_number': "AAAAB",
        'model': "LC27T55",
        'manufacturer': "Samsung",
        'generation': 1,
        'weight': 0.1,
        'height': 0.1,
        'depth': 0.1,
        'id_device_supplier': "b2",
    }
    user3.post(uri, data=data)
    dev = Device.query.one()
    dhid = dev.dhid
    assert dev.phid() == '1'
    uri = f'/inventory/binding/{dhid}/1/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert 'is not a Snapshot device!' in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_bug_3831_documents(user3: UserClientFlask):
    uri = '/inventory/lot/add/'
    user3.get(uri)
    lot_name = 'lot1'
    data = {
        'name': lot_name,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data)
    lot = Lot.query.filter_by(name=lot_name).one()

    lot_id = lot.id
    uri = f'/inventory/lot/{lot_id}/transfer-document/add/'
    body, status = user3.get(uri)
    txt = 'Error, this lot is not a transfer lot.'

    assert status == '200 OK'
    assert txt in body

    uri = f'/inventory/lot/{lot_id}/transfer/incoming/'
    user3.get(uri)
    data = {'csrf_token': generate_csrf(), 'code': 'AAA', 'lot_name': lot_name}

    body, status = user3.post(uri, data=data)
    assert status == '200 OK'
    assert 'Transfer created successfully!' in body
    assert 'Delete Lot' in body
    assert 'Incoming Lot' in body

    lot_id = Lot.query.all()[1].id
    uri = f'/inventory/lot/{lot_id}/transfer-document/add/'
    body, status = user3.get(uri)

    b_file = b'1234567890'
    file_name = "my_file.doc"
    file_upload = (BytesIO(b_file), file_name)

    data = {
        'csrf_token': generate_csrf(),
        'url': "",
        'description': "",
        'document_id': "",
        'date': "",
        'file': file_upload,
    }

    uri = f'/inventory/lot/{lot_id}/transfer-document/add/'
    body, status = user3.post(uri, data=data, content_type="multipart/form-data")
    assert status == '200 OK'

    # Second document
    uri = f'/inventory/lot/{lot_id}/transfer-document/add/'
    file_upload = (BytesIO(b_file), file_name)
    data['file'] = file_upload
    data['csrf_token'] = generate_csrf()
    body, status = user3.post(uri, data=data, content_type="multipart/form-data")
    assert status == '200 OK'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_hdd_filter(user3: UserClientFlask):
    create_device(user3, 'real-eee-1001pxd.snapshot.12.json')

    hdds = Device.query.filter_by(type='HardDrive').all()
    for hdd in hdds:
        hdd.parent = None
    db.session.commit()

    csrf = generate_csrf()
    uri = f'/inventory/device/?filter=All+DataStorage&csrf_token={csrf}'
    body, status = user3.get(uri)

    assert status == '200 OK'
    for hdd in hdds:
        assert hdd.dhid in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_kangaroo(user3: UserClientFlask):
    create_device(user3, 'real-eee-1001pxd.snapshot.12.json')

    body, status = user3.get('/workbench/')

    assert status == '200 OK'

    pc = Device.query.filter_by(type='Laptop').first()
    data = {
        'csrf_token': generate_csrf(),
        'phid': pc.phid(),
    }

    body, status = user3.post('/workbench/', data=data)
    assert status == '200 OK'
    assert pc.phid() in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_drop_kangaroo(user3: UserClientFlask):
    create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    pc = Device.query.filter_by(type='Laptop').first()
    phid = 'AAA'
    pc.placeholder.phid = phid
    db.session.commit()

    body, status = user3.get('/workbench/')
    assert phid not in body

    data = {
        'csrf_token': generate_csrf(),
        'phid': phid,
    }

    body, status = user3.post('/workbench/', data=data)
    assert status == '200 OK'
    assert phid in body

    placeholder_id = pc.placeholder.id
    uri = f'/workbench/erasure_host/{placeholder_id}/'
    body, status = user3.get(uri)
    assert status == '200 OK'
    assert phid not in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_filter_hdd_in_kangaroo(user3: UserClientFlask):
    create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    csrf = generate_csrf()
    uri = f'/inventory/device/?filter=All+DataStorage&csrf_token={csrf}'
    body, status = user3.get(uri)

    assert status == '200 OK'
    for hdd in Device.query.filter_by(type='HardDrive').all():
        assert hdd.dhid not in body

    user3.get('/workbench/')
    pc = Device.query.filter_by(type='Laptop').first()
    data = {
        'csrf_token': generate_csrf(),
        'phid': pc.phid(),
    }
    user3.post('/workbench/', data=data)

    csrf = generate_csrf()
    uri = f'/inventory/device/?filter=All+DataStorage&csrf_token={csrf}'
    body, status = user3.get(uri)

    assert status == '200 OK'
    for hdd in Device.query.filter_by(type='HardDrive').all():
        assert hdd.dhid in body


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_is_server_erase(user3: UserClientFlask):
    snapshot = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')

    user3.get('/workbench/')
    data = {
        'csrf_token': generate_csrf(),
        'phid': snapshot.device.phid(),
    }
    user3.post('/workbench/', data=data)

    uri = '/inventory/upload-snapshot/'
    file_name = 'real-eee-1001pxd.snapshot.12'
    snapshot_json = conftest.yaml2json(file_name)
    snapshot_json['uuid'] = 'c058e8d2-fb92-47cb-a4b7-522b75561136'
    b_snapshot = bytes(json.dumps(snapshot_json), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)
    user3.get(uri)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    snapshot2 = Snapshot.query.filter_by(uuid=snapshot_json['uuid']).one()

    assert not snapshot.is_server_erase
    assert snapshot2.is_server_erase
    assert snapshot in snapshot.device.actions
    assert snapshot2 in snapshot.device.actions


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_system_uuid_motherboard(user3: UserClientFlask):
    # we want to do an snapshot log when there are the same system-uuid for
    # 2 computers with diferent motherboard
    snapshot = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')

    uri = '/inventory/upload-snapshot/'
    file_name = 'real-eee-1001pxd.snapshot.12'
    snapshot_json = conftest.yaml2json(file_name)
    snapshot_json['uuid'] = 'c058e8d2-fb92-47cb-a4b7-522b75561136'
    for c in snapshot_json['components']:
        if c['type'] == 'Motherboard':
            c['serialNumber'] = 'ABee0123456720'
    b_snapshot = bytes(json.dumps(snapshot_json), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)
    user3.get(uri)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    snapshot2 = Snapshot.query.filter_by(uuid=snapshot_json['uuid']).first()
    assert snapshot2.device == snapshot.device
    for c in snapshot.device.components:
        if c.type == 'Motherboard':
            assert c.serial_number == 'abee0123456720'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_unreliable_device(user3: UserClientFlask):
    # Create device
    snapshot = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')

    # Update device
    uri = '/inventory/upload-snapshot/'
    file_name = 'real-eee-1001pxd.snapshot.12'
    snapshot_json = conftest.yaml2json(file_name)
    snapshot_json['uuid'] = 'c058e8d2-fb92-47cb-a4b7-522b75561136'
    b_snapshot = bytes(json.dumps(snapshot_json), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)
    user3.get(uri)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    snapshot2 = Snapshot.query.filter_by(uuid=snapshot_json['uuid']).first()
    assert snapshot2.device == snapshot.device
    assert Snapshot.query.count() == 2
    snapshots = Snapshot.query.all()
    assert snapshots[0].device == snapshots[1].device
    assert len(snapshots[0].device.components)
    assert snapshot2 in snapshots

    # Change update for new device
    uuid2 = snapshot2.uuid
    uri = f"/inventory/snapshots/{uuid2}/"
    user3.get(uri)

    data = {
        'snapshot_type': "new_device",
        'csrf_token': generate_csrf(),
    }
    assert Device.query.filter_by(hid=snapshot.device.hid).count() == 2
    user3.post(uri, data=data)
    assert Device.query.filter_by(hid=snapshot.device.hid).count() == 4
    assert Snapshot.query.count() == 2
    snapshots = Snapshot.query.all()
    assert snapshot2 not in snapshots
    assert snapshots[0].device != snapshots[1].device
    assert len(snapshots[0].device.components) == 8
    assert len(snapshots[1].device.components) == 9
    assert len(snapshots[0].device.actions) == 11
    assert len(snapshots[1].device.actions) == 10


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_reliable_device(user3: UserClientFlask):
    # Create device
    snapshot = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')

    # Update device
    uri = '/inventory/upload-snapshot/'
    file_name = 'real-eee-1001pxd.snapshot.12'
    snapshot_json = conftest.yaml2json(file_name)
    snapshot_json['uuid'] = 'c058e8d2-fb92-47cb-a4b7-522b75561136'
    b_snapshot = bytes(json.dumps(snapshot_json), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)
    user3.get(uri)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    snapshot2 = Snapshot.query.filter_by(uuid=snapshot_json['uuid']).first()

    # Change update for new device
    uuid2 = snapshot2.uuid
    uri = f"/inventory/snapshots/{uuid2}/"
    user3.get(uri)

    data = {
        'snapshot_type': "new_device",
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data)

    # Change update for update
    snapshot3 = Snapshot.query.all()[-1]
    uuid3 = snapshot3.uuid
    uri = f"/inventory/snapshots/{uuid3}/"
    user3.get(uri)

    data = {
        'snapshot_type': "update",
        'csrf_token': generate_csrf(),
    }
    assert Device.query.filter_by(hid=snapshot.device.hid).count() == 4
    user3.post(uri, data=data)
    assert Device.query.filter_by(hid=snapshot.device.hid).count() == 2
    assert Snapshot.query.count() == 1
    assert Snapshot.query.first() == snapshot
    assert len(snapshot.device.components) == 8
    assert len(snapshot.device.actions) == 7


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_device_document(user3: UserClientFlask):
    snapshot = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    device = Device.query.filter_by(devicehub_id=snapshot.device.dhid).one()
    uri = '/inventory/device/{}/document/add/'.format(device.dhid)
    user3.get(uri)

    name = "doc1.pdf"
    url = "https://www.usody.com/"
    file_name = (BytesIO(b'1234567890'), name)
    data = {
        'url': url,
        'file_name': file_name,
        'csrf_token': generate_csrf(),
    }

    user3.post(uri, data=data, content_type="multipart/form-data")
    assert device.documents[0].file_name == name
    assert device.documents[0].url.to_text() == url


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_edit_device_document(user3: UserClientFlask):
    snapshot = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    device = Device.query.filter_by(devicehub_id=snapshot.device.dhid).one()
    uri = '/inventory/device/{}/document/add/'.format(device.dhid)
    user3.get(uri)

    name = "doc1.pdf"
    url = "https://www.usody.com/"
    file_name = (BytesIO(b'1234567890'), name)
    data = {
        'url': url,
        'file_name': file_name,
        'csrf_token': generate_csrf(),
    }

    user3.post(uri, data=data, content_type="multipart/form-data")

    doc_id = str(device.documents[0].id)
    uri = '/inventory/device/{}/document/edit/{}'.format(device.dhid, doc_id)
    user3.get(uri)

    data['url'] = "https://www.ereuse.org/"
    data['csrf_token'] = generate_csrf()
    data['file_name'] = (BytesIO(b'1234567890'), name)

    user3.post(uri, data=data, content_type="multipart/form-data")
    assert device.documents[0].file_name == name
    assert device.documents[0].url.to_text() == data['url']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_delete_device_document(user3: UserClientFlask):
    snapshot = create_device(user3, 'real-eee-1001pxd.snapshot.12.json')
    device = Device.query.filter_by(devicehub_id=snapshot.device.dhid).one()
    uri = '/inventory/device/{}/document/add/'.format(device.dhid)
    user3.get(uri)

    name = "doc1.pdf"
    url = "https://www.usody.com/"
    file_name = (BytesIO(b'1234567890'), name)
    data = {
        'url': url,
        'file_name': file_name,
        'csrf_token': generate_csrf(),
    }

    user3.post(uri, data=data, content_type="multipart/form-data")

    doc_id = str(device.documents[0].id)
    uri = '/inventory/device/{}/document/del/{}'.format(device.dhid, doc_id)
    user3.get(uri)
    assert len(device.documents) == 0
