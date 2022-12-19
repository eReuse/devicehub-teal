import json
from io import BytesIO

import pytest
from flask_wtf.csrf import generate_csrf

from ereuse_devicehub.client import UserClient, UserClientFlask
from ereuse_devicehub.resources.action.models import Snapshot
from ereuse_devicehub.resources.device.models import Computer
from tests import conftest


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_form(user3: UserClientFlask):
    uri = '/inventory/upload-snapshot/'
    file_name = 'system_uuid1.json'
    user3.get(uri)

    snapshot = conftest.file_json(file_name)
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")

    db_snapthot = Snapshot.query.one()
    device = db_snapthot.device
    assert device.hid == 'laptop-toshiba-satellite_l655-2b335208q'
    assert str(device.system_uuid) == 'f0dc6a7f-c23f-e011-b5d0-00266caeee78'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_api(user: UserClient):
    file_name = 'system_uuid1.json'
    snapshot_11 = conftest.file_json(file_name)
    user.post(snapshot_11, res=Snapshot)

    db_snapthot = Snapshot.query.one()
    device = db_snapthot.device
    assert device.hid == 'laptop-toshiba-satellite_l655-2b335208q'
    assert str(device.system_uuid) == 'f0dc6a7f-c23f-e011-b5d0-00266caeee78'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wbLite_form(user3: UserClientFlask):
    uri = '/inventory/upload-snapshot/'
    file_name = 'system_uuid2.json'
    user3.get(uri)

    snapshot = conftest.file_json(file_name)
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")

    db_snapthot = Snapshot.query.one()
    device = db_snapthot.device
    assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
    assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wbLite_api(user: UserClient):
    snapshot_lite = conftest.file_json('system_uuid2.json')

    user.post(snapshot_lite, uri="/api/inventory/")

    db_snapthot = Snapshot.query.one()
    device = db_snapthot.device
    assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
    assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_to_wb11_with_uuid_api(user: UserClient):

    # insert computer with wb11 with hid and without uuid, (old version)
    snapshot_11 = conftest.file_json('system_uuid3.json')
    user.post(snapshot_11, res=Snapshot)

    db_snapthot = Snapshot.query.one()
    device = db_snapthot.device
    assert Computer.query.count() == 2
    assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
    assert device.system_uuid is None

    # insert the same computer with wb11 with hid and with uuid, (new version)
    snapshot_lite = conftest.file_json('system_uuid2.json')
    snapshot_11['debug'] = {'lshw': snapshot_lite['data']['lshw']}
    snapshot_11['uuid'] = '0973fda0-589a-11eb-ae93-0242ac130003'
    user.post(snapshot_11, res=Snapshot)

    assert (
        snapshot_11['debug']['lshw']['configuration']['uuid']
        == '364ee69c-9c82-9cb1-2111-88ae1da6f3d0'
    )
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert device.system_uuid is None


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_with_uuid_to_wb11_api(user: UserClient):

    # insert computer with wb11 with hid and without uuid, (old version)
    snapshot_11 = conftest.file_json('system_uuid3.json')
    snapshot_lite = conftest.file_json('system_uuid2.json')
    snapshot_11['debug'] = {'lshw': snapshot_lite['data']['lshw']}
    snapshot_11['uuid'] = '0973fda0-589a-11eb-ae93-0242ac130003'
    user.post(snapshot_11, res=Snapshot)

    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'

    # insert the same computer with wb11 with hid and with uuid, (new version)
    snapshot_11 = conftest.file_json('system_uuid3.json')
    assert 'debug' not in snapshot_11
    user.post(snapshot_11, res=Snapshot)

    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_with_uuid_to_wb11_without_hid_api(user: UserClient):

    # insert computer with wb11 with hid and without uuid, (old version)
    snapshot_11 = conftest.file_json('system_uuid3.json')
    snapshot_lite = conftest.file_json('system_uuid2.json')
    snapshot_11['debug'] = {'lshw': snapshot_lite['data']['lshw']}
    snapshot_11['uuid'] = '0973fda0-589a-11eb-ae93-0242ac130003'
    user.post(snapshot_11, res=Snapshot)

    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'

    # insert the same computer with wb11 with hid and with uuid, (new version)
    snapshot_11 = conftest.file_json('system_uuid3.json')
    components = [x for x in snapshot_11['components'] if x['type'] != 'NetworkAdapter']
    snapshot_11['components'] = components
    snapshot_11['debug'] = {'lshw': snapshot_lite['data']['lshw']}
    user.post(snapshot_11, res=Snapshot)

    assert Computer.query.count() == 2


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_to_wb11_with_uuid_form(user3: UserClientFlask):

    # insert computer with wb11 with hid and without uuid, (old version)
    uri = '/inventory/upload-snapshot/'
    user3.get(uri)

    file_name = 'system_uuid3.json'
    snapshot = conftest.file_json(file_name)
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")

    db_snapthot = Snapshot.query.one()
    device = db_snapthot.device
    assert Computer.query.count() == 2
    assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
    assert device.system_uuid is None

    # insert the same computer with wb11 with hid and with uuid, (new version)
    snapshot_lite = conftest.file_json('system_uuid2.json')
    snapshot['debug'] = {'lshw': snapshot_lite['data']['lshw']}
    snapshot['uuid'] = '0973fda0-589a-11eb-ae93-0242ac130003'
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")

    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert device.system_uuid is None


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_with_uuid_to_wb11_form(user3: UserClientFlask):

    # insert computer with wb11 with hid and without uuid, (old version)
    uri = '/inventory/upload-snapshot/'
    user3.get(uri)

    file_name = 'system_uuid3.json'
    snapshot_lite = conftest.file_json('system_uuid2.json')
    snapshot = conftest.file_json(file_name)
    snapshot['debug'] = {'lshw': snapshot_lite['data']['lshw']}
    snapshot['uuid'] = '0973fda0-589a-11eb-ae93-0242ac130003'
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")

    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'

    # insert the same computer with wb11 with hid and with uuid, (new version)
    snapshot = conftest.file_json('system_uuid3.json')
    assert 'debug' not in snapshot
    b_snapshot = bytes(json.dumps(snapshot), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")

    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_with_uuid_to_wb11_without_hid_form(user3: UserClientFlask):

    uri = '/inventory/upload-snapshot/'
    user3.get(uri)

    # insert computer with wb11 with hid and without uuid, (old version)
    snapshot_lite = conftest.file_json('system_uuid2.json')
    file_name = 'system_uuid3.json'
    snapshot_11 = conftest.file_json(file_name)
    snapshot_11['debug'] = {'lshw': snapshot_lite['data']['lshw']}
    snapshot_11['uuid'] = '0973fda0-589a-11eb-ae93-0242ac130003'
    b_snapshot = bytes(json.dumps(snapshot_11), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")

    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'

    # insert the same computer with wb11 with hid and with uuid, (new version)
    snapshot_11 = conftest.file_json('system_uuid3.json')
    components = [x for x in snapshot_11['components'] if x['type'] != 'NetworkAdapter']
    snapshot_11['components'] = components
    snapshot_11['debug'] = {'lshw': snapshot_lite['data']['lshw']}
    b_snapshot = bytes(json.dumps(snapshot_11), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")

    assert Computer.query.count() == 2


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_to_wblite_api(user: UserClient):

    # insert computer with wb11 with hid and without uuid, (old version)
    snapshot_11 = conftest.file_json('system_uuid3.json')
    user.post(snapshot_11, res=Snapshot)
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert device.system_uuid is None

    snapshot_lite = conftest.file_json('system_uuid2.json')
    user.post(snapshot_lite, uri="/api/inventory/")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            # assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'
            assert device.system_uuid is None


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wblite_to_wb11_api(user: UserClient):

    snapshot_lite = conftest.file_json('system_uuid2.json')
    user.post(snapshot_lite, uri="/api/inventory/")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'

    snapshot_11 = conftest.file_json('system_uuid3.json')
    user.post(snapshot_11, res=Snapshot)
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_to_wblite_form(user3: UserClientFlask):

    uri = '/inventory/upload-snapshot/'
    user3.get(uri)

    file_name = 'system_uuid3.json'
    snapshot_11 = conftest.file_json(file_name)
    b_snapshot = bytes(json.dumps(snapshot_11), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert device.system_uuid is None

    file_name = 'system_uuid2.json'
    snapshot_lite = conftest.file_json(file_name)
    b_snapshot = bytes(json.dumps(snapshot_lite), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            # assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'
            assert device.system_uuid is None


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wblite_to_wb11_form(user3: UserClientFlask):

    uri = '/inventory/upload-snapshot/'
    user3.get(uri)

    file_name = 'system_uuid2.json'
    snapshot_lite = conftest.file_json(file_name)
    b_snapshot = bytes(json.dumps(snapshot_lite), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid == 'laptop-acer-aohappy-lusea0d010038879a01601'
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'

    file_name = 'system_uuid3.json'
    snapshot_11 = conftest.file_json(file_name)
    b_snapshot = bytes(json.dumps(snapshot_11), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wblite_to_wblite_api(user: UserClient):

    snapshot_lite = conftest.file_json('system_uuid2.json')
    user.post(snapshot_lite, uri="/api/inventory/")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'

    snapshot_lite = conftest.file_json('system_uuid2.json')
    snapshot_lite['uuid'] = '0973fda0-589a-11eb-ae93-0242ac130003'
    user.post(snapshot_lite, uri="/api/inventory/")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wblite_to_wblite_form(user3: UserClientFlask):

    uri = '/inventory/upload-snapshot/'
    user3.get(uri)

    file_name = 'system_uuid2.json'
    snapshot_lite = conftest.file_json(file_name)
    b_snapshot = bytes(json.dumps(snapshot_lite), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'

    file_name = 'system_uuid2.json'
    snapshot_lite = conftest.file_json(file_name)
    snapshot_lite['uuid'] = '0973fda0-589a-11eb-ae93-0242ac130003'
    b_snapshot = bytes(json.dumps(snapshot_lite), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid
            assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_to_wb11_duplicity_api(user: UserClient):

    # insert computer with wb11 with hid and without uuid, (old version)
    snapshot_11 = conftest.file_json('system_uuid3.json')
    user.post(snapshot_11, res=Snapshot)
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid
            assert device.system_uuid is None

    snapshot_11 = conftest.file_json('system_uuid3.json')
    snapshot_11['uuid'] = '0973fda0-589a-11eb-ae93-0242ac130003'
    components = [x for x in snapshot_11['components'] if x['type'] != 'NetworkAdapter']
    snapshot_11['components'] = components
    user.post(snapshot_11, res=Snapshot)
    assert Computer.query.count() == 2
    for c in Computer.query.all():
        assert 'laptop-acer-aohappy-lusea0d010038879a01601' in c.hid
        assert c.system_uuid is None


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_to_wb11_duplicity_form(user3: UserClientFlask):

    uri = '/inventory/upload-snapshot/'
    user3.get(uri)

    file_name = 'system_uuid3.json'
    snapshot_11 = conftest.file_json(file_name)
    b_snapshot = bytes(json.dumps(snapshot_11), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid
            assert device.system_uuid is None

    snapshot_11 = conftest.file_json('system_uuid3.json')
    snapshot_11['uuid'] = '0973fda0-589a-11eb-ae93-0242ac130003'
    components = [x for x in snapshot_11['components'] if x['type'] != 'NetworkAdapter']
    snapshot_11['components'] = components

    b_snapshot = bytes(json.dumps(snapshot_11), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")

    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert 'laptop-acer-aohappy-lusea0d010038879a01601' in device.hid
            assert device.system_uuid is None


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_smbios_2_5_api(user: UserClient):

    # insert computer with wb11 with hid and without uuid, (old version)
    snapshot_11 = conftest.file_json('system_uuid4.json')
    user.post(snapshot_11, res=Snapshot)
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid
            assert device.system_uuid is None


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wb11_smbios_2_5_form(user3: UserClientFlask):

    uri = '/inventory/upload-snapshot/'
    user3.get(uri)

    file_name = 'system_uuid4.json'
    snapshot_11 = conftest.file_json(file_name)
    b_snapshot = bytes(json.dumps(snapshot_11), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid
            assert device.system_uuid is None


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wblite_smbios_2_5_api(user: UserClient):

    # insert computer with wb11 with hid and without uuid, (old version)
    snapshot_lite = conftest.file_json('system_uuid2.json')
    snapshot_lite['data']['lshw']['capabilities']['smbios-3.0'] = 'SMBIOS version 2.5'
    user.post(snapshot_lite, uri="/api/inventory/")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid
        assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_wblite_smbios_2_5_form(user3: UserClientFlask):

    uri = '/inventory/upload-snapshot/'
    user3.get(uri)

    file_name = 'system_uuid2.json'
    snapshot_lite = conftest.file_json(file_name)
    snapshot_lite['data']['lshw']['capabilities']['smbios-3.0'] = 'SMBIOS version 2.5'
    b_snapshot = bytes(json.dumps(snapshot_lite), 'utf-8')
    file_snap = (BytesIO(b_snapshot), file_name)

    data = {
        'snapshot': file_snap,
        'csrf_token': generate_csrf(),
    }
    user3.post(uri, data=data, content_type="multipart/form-data")
    assert Computer.query.count() == 2
    for device in Computer.query.all():
        if device.binding:
            assert device.hid
        assert str(device.system_uuid) == '9ce64e36-829c-b19c-2111-88ae1da6f3d0'
