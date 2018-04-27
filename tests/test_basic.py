import pytest

from ereuse_devicehub.devicehub import Devicehub


def test_dependencies():
    with pytest.raises(ImportError):
        # Simplejson has a different signature than stdlib json
        # should be fixed though
        # noinspection PyUnresolvedReferences
        import simplejson


# noinspection PyArgumentList
def test_init(app: Devicehub):
    """Tests app initialization."""
    pass
