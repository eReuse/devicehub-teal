import pytest

from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.client import Client


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
        import simplejson


# noinspection PyArgumentList
@pytest.mark.mvp
def test_api_docs(client: Client):
    """Tests /apidocs correct initialization."""
    docs, _ = client.get('/apidocs')
    assert set(docs['paths'].keys()) == {
        '/actions/',
        '/apidocs',
        '/api/inventory/',
        '/allocates/',
        '/deallocates/',
        '/deliverynotes/',
        '/devices/',
        '/devices/static/{filename}',
        '/documents/static/{filename}',
        '/documents/actions/',
        '/documents/erasures/',
        '/documents/devices/',
        '/documents/stamps/',
        '/documents/wbconf/{wbtype}',
        '/documents/internalstats/',
        '/documents/stock/',
        '/documents/check/',
        '/documents/lots/',
        '/versions/',
        '/manufacturers/',
        '/licences/',
        '/lives/',
        '/lots/',
        '/lots/{id}/children',
        '/lots/{id}/devices',
        '/metrics/',
        '/tags/',
        '/tags/{tag_id}/device/{device_id}',
        '/trade-documents/',
        '/users/',
        '/users/login/',
        '/users/logout/',
    }
    assert docs['info'] == {'title': 'Devicehub', 'version': '0.2'}
    assert docs['components']['securitySchemes']['bearerAuth'] == {
        'description': 'Basic scheme with token.',
        'in': 'header',
        'description:': 'HTTP Basic scheme',
        'type': 'http',
        'scheme': 'basic',
        'name': 'Authorization'
    }
    assert len(docs['definitions']) == 132
