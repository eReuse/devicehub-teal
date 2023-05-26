import pytest

from ereuse_devicehub.client import Client
from ereuse_devicehub.devicehub import Devicehub


@pytest.mark.mvp
def test_dummy(_app: Devicehub):
    """Tests the dummy cli command."""
    runner = _app.test_cli_runner()
    runner.invoke('dummy', '--yes')
    with _app.app_context():
        _app.db.drop_all()


@pytest.mark.mvp
def test_dependencies():
    with pytest.raises(ImportError):
        # Simplejson has a different signature than stdlib json
        # should be fixed though
        # noinspection PyUnresolvedReferences
        import simplejson  # noqa: F401


# noinspection PyArgumentList
@pytest.mark.mvp
def test_api_docs(client: Client):
    """Tests /apidocs correct initialization."""
    docs, _ = client.get('/apidocs')
    assert set(docs['paths'].keys()) == {
        '/',
        '/actions/',
        '/allocates/',
        '/apidocs',
        '/api/inventory/',
        '/deallocates/',
        '/deliverynotes/',
        '/devices/',
        '/devices/static/{filename}',
        '/documents/actions/',
        '/documents/check/',
        '/documents/devices/',
        '/documents/erasures/',
        '/documents/lots/',
        '/inventory/search/',
        '/documents/stamps/',
        '/documents/static/{filename}',
        '/documents/stock/',
        '/documents/wbconf/{wbtype}',
        '/inventory/action/add/',
        '/inventory/action/allocate/add/',
        '/inventory/action/datawipe/add/',
        '/inventory/action/trade/add/',
        '/inventory/device/',
        '/inventory/device/add/',
        '/inventory/device/{id}/',
        '/inventory/device/{dhid}/binding/',
        '/inventory/device/{dhid}/document/del/{doc_id}',
        '/inventory/device/{dhid}/document/edit/{doc_id}',
        '/inventory/device/{dhid}/document/add/',
        '/inventory/device/erasure/',
        '/inventory/device/erasure/{orphans}/',
        '/inventory/all/device/',
        '/inventory/export/{export_id}/',
        '/inventory/lot/add/',
        '/inventory/lot/{id}/',
        '/inventory/lot/{id}/del/',
        '/inventory/lot/{lot_id}/device/',
        '/inventory/lot/{lot_id}/device/add/',
        '/inventory/lot/{lot_id}/deliverynote/',
        '/inventory/lot/{lot_id}/receivernote/',
        '/inventory/lot/{lot_id}/transfer-document/add/',
        '/inventory/lot/{lot_id}/transfer/{type_id}/',
        '/inventory/lot/{lot_id}/opentransfer/',
        '/inventory/lot/{lot_id}/transfer/',
        '/inventory/lot/transfer/{type_id}/',
        '/inventory/lot/{lot_id}/upload-snapshot/',
        '/inventory/lot/{lot_id}/customerdetails/',
        '/inventory/lot/{lot_id}/document/edit/{doc_id}',
        '/inventory/lot/{lot_id}/document/del/{doc_id}',
        '/inventory/snapshots/{snapshot_uuid}/',
        '/inventory/snapshots/',
        '/inventory/tag/devices/{dhid}/add/',
        '/inventory/tag/devices/{dhid}/del/',
        '/inventory/upload-snapshot/',
        '/inventory/device/edit/{id}/',
        '/inventory/upload-placeholder/',
        '/inventory/lot/{lot_id}/upload-placeholder/',
        '/inventory/placeholder-logs/',
        '/inventory/unbinding/{phid}/',
        '/inventory/binding/{dhid}/{phid}/',
        '/labels/',
        '/labels/add/',
        '/labels/print',
        '/labels/unnamed/add/',
        '/labels/{id}/',
        '/licences/',
        '/lives/',
        '/login/',
        '/logout/',
        '/lots/',
        '/lots/{id}/children',
        '/lots/{id}/devices',
        '/manufacturers/',
        '/metrics/',
        '/profile/',
        '/set_password/',
        '/set_sanitization/',
        '/tags/',
        '/tags/{tag_id}/device/{device_id}',
        '/trade-documents/',
        '/users/',
        '/users/login/',
        '/users/logout/',
        '/versions/',
        '/workbench/',
        '/workbench/erasure_host/{id}/',
    }
    assert docs['info'] == {'title': 'Devicehub', 'version': '0.2'}
    assert docs['components']['securitySchemes']['bearerAuth'] == {
        'description': 'Basic scheme with token.',
        'in': 'header',
        'description:': 'HTTP Basic scheme',
        'type': 'http',
        'scheme': 'basic',
        'name': 'Authorization',
    }
    assert len(docs['definitions']) == 135
