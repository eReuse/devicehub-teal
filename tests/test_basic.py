import pytest

from ereuse_devicehub.client import Client


def test_dependencies():
    with pytest.raises(ImportError):
        # Simplejson has a different signature than stdlib json
        # should be fixed though
        # noinspection PyUnresolvedReferences
        import simplejson


# noinspection PyArgumentList
def test_api_docs(client: Client):
    """Tests /apidocs correct initialization."""
    docs, _ = client.get('/apidocs')
    assert set(docs['paths'].keys()) == {
        # todo this does not appear: '/tags/{id}/device',
        '/apidocs',
        '/users/',
        '/devices/',
        '/tags/',
        '/snapshots/',
        '/users/login',
        '/events/',
        '/lots/',
        '/manufacturers/',
        '/lots/{id}/children',
        '/lots/{id}/devices',
        '/tags/{tag_id}/device/{device_id}',
        '/devices/static/{filename}'
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
    assert 92 == len(docs['definitions'])
