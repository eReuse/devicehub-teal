import pytest

from ereuse_devicehub import __version__
from ereuse_devicehub.client import Client


@pytest.mark.mvp
def test_get_version(client: Client):
    """Checks GETting versions of services."""

    content, res = client.get("/versions/", None)

    version = {'devicehub': __version__, 'ereuse_tag': '0.0.0'}
    assert res.status_code == 200
    assert content == version
