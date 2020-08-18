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
        '/batteries/{id}/merge/',
        '/bikes/{id}/merge/',
        '/cameras/{id}/merge/',
        '/cellphones/{id}/merge/',
        '/components/{id}/merge/',
        '/computer-accessories/{id}/merge/',
        '/computer-monitors/{id}/merge/',
        '/computers/{id}/merge/',
        '/cookings/{id}/merge/',
        '/data-storages/{id}/merge/',
        '/dehumidifiers/{id}/merge/',
        '/deliverynotes/',
        '/desktops/{id}/merge/',
        '/devices/',
        '/devices/static/{filename}',
        '/devices/{id}/merge/',
        '/displays/{id}/merge/',
        '/diy-and-gardenings/{id}/merge/',
        '/documents/devices/',
        '/documents/erasures/',
        '/documents/lots/',
        '/documents/static/{filename}',
        '/documents/stock/',
        '/drills/{id}/merge/',
        '/graphic-cards/{id}/merge/',
        '/hard-drives/{id}/merge/',
        '/homes/{id}/merge/',
        '/hubs/{id}/merge/',
        '/keyboards/{id}/merge/',
        '/label-printers/{id}/merge/',
        '/laptops/{id}/merge/',
        '/lots/',
        '/lots/{id}/children',
        '/lots/{id}/devices',
        '/manufacturers/',
        '/memory-card-readers/{id}/merge/',
        '/mice/{id}/merge/',
        '/microphones/{id}/merge/',
        '/mixers/{id}/merge/',
        '/mobiles/{id}/merge/',
        '/monitors/{id}/merge/',
        '/motherboards/{id}/merge/',
        '/network-adapters/{id}/merge/',
        '/networkings/{id}/merge/',
        '/pack-of-screwdrivers/{id}/merge/',
        '/printers/{id}/merge/',
        '/processors/{id}/merge/',
        '/proofs/',
        '/rackets/{id}/merge/',
        '/ram-modules/{id}/merge/',
        '/recreations/{id}/merge/',
        '/routers/{id}/merge/',
        '/sais/{id}/merge/',
        '/servers/{id}/merge/',
        '/smartphones/{id}/merge/',
        '/solid-state-drives/{id}/merge/',
        '/sound-cards/{id}/merge/',
        '/sounds/{id}/merge/',
        '/stairs/{id}/merge/',
        '/switches/{id}/merge/',
        '/tablets/{id}/merge/',
        '/tags/',
        '/tags/{tag_id}/device/{device_id}',
        '/television-sets/{id}/merge/',
        '/users/',
        '/users/login/',
        '/video-scalers/{id}/merge/',
        '/videoconferences/{id}/merge/',
        '/videos/{id}/merge/',
        '/wireless-access-points/{id}/merge/'
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
    assert len(docs['definitions']) == 122
