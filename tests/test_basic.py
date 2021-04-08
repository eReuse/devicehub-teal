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
        '/trades/',
        '/users/',
        '/users/login/'
        # '/devices/{dev1_id}/merge/{dev2_id}',
        # '/batteries/{dev1_id}/merge/{dev2_id}',
        # '/bikes/{dev1_id}/merge/{dev2_id}',
        # '/cameras/{dev1_id}/merge/{dev2_id}',
        # '/cellphones/{dev1_id}/merge/{dev2_id}',
        # '/components/{dev1_id}/merge/{dev2_id}',
        # '/computer-accessories/{dev1_id}/merge/{dev2_id}',
        # '/computer-monitors/{dev1_id}/merge/{dev2_id}',
        # '/computers/{dev1_id}/merge/{dev2_id}',
        # '/cookings/{dev1_id}/merge/{dev2_id}',
        # '/data-storages/{dev1_id}/merge/{dev2_id}',
        # '/dehumidifiers/{dev1_id}/merge/{dev2_id}',
        # '/desktops/{dev1_id}/merge/{dev2_id}',
        # '/displays/{dev1_id}/merge/{dev2_id}',
        # '/diy-and-gardenings/{dev1_id}/merge/{dev2_id}',
        # '/drills/{dev1_id}/merge/{dev2_id}',
        # '/graphic-cards/{dev1_id}/merge/{dev2_id}',
        # '/hard-drives/{dev1_id}/merge/{dev2_id}',
        # '/homes/{dev1_id}/merge/{dev2_id}',
        # '/hubs/{dev1_id}/merge/{dev2_id}',
        # '/keyboards/{dev1_id}/merge/{dev2_id}',
        # '/label-printers/{dev1_id}/merge/{dev2_id}',
        # '/laptops/{dev1_id}/merge/{dev2_id}',
        # '/memory-card-readers/{dev1_id}/merge/{dev2_id}',
        # '/mice/{dev1_id}/merge/{dev2_id}',
        # '/microphones/{dev1_id}/merge/{dev2_id}',
        # '/mixers/{dev1_id}/merge/{dev2_id}',
        # '/mobiles/{dev1_id}/merge/{dev2_id}',
        # '/monitors/{dev1_id}/merge/{dev2_id}',
        # '/motherboards/{dev1_id}/merge/{dev2_id}',
        # '/network-adapters/{dev1_id}/merge/{dev2_id}',
        # '/networkings/{dev1_id}/merge/{dev2_id}',
        # '/pack-of-screwdrivers/{dev1_id}/merge/{dev2_id}',
        # '/printers/{dev1_id}/merge/{dev2_id}',
        # '/processors/{dev1_id}/merge/{dev2_id}',
        # '/rackets/{dev1_id}/merge/{dev2_id}',
        # '/ram-modules/{dev1_id}/merge/{dev2_id}',
        # '/recreations/{dev1_id}/merge/{dev2_id}',
        # '/routers/{dev1_id}/merge/{dev2_id}',
        # '/sais/{dev1_id}/merge/{dev2_id}',
        # '/servers/{dev1_id}/merge/{dev2_id}',
        # '/smartphones/{dev1_id}/merge/{dev2_id}',
        # '/solid-state-drives/{dev1_id}/merge/{dev2_id}',
        # '/sound-cards/{dev1_id}/merge/{dev2_id}',
        # '/sounds/{dev1_id}/merge/{dev2_id}',
        # '/stairs/{dev1_id}/merge/{dev2_id}',
        # '/switches/{dev1_id}/merge/{dev2_id}',
        # '/tablets/{dev1_id}/merge/{dev2_id}',
        # '/television-sets/{dev1_id}/merge/{dev2_id}',
        # '/video-scalers/{dev1_id}/merge/{dev2_id}',
        # '/videoconferences/{dev1_id}/merge/{dev2_id}',
        # '/videos/{dev1_id}/merge/{dev2_id}',
        # '/wireless-access-points/{dev1_id}/merge/{dev2_id}',
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
    assert len(docs['definitions']) == 119
