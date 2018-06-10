from uuid import UUID

import pytest

from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.resources.user import Organization


@pytest.mark.usefixtures('app_context')
def test_default_org_exists(config: DevicehubConfig):
    """
    Ensures that the default organization is created on app
    initialization and that is accessible for the method
    :meth:`ereuse_devicehub.resources.user.Organization.get_default_org`.
    """
    assert Organization.query.filter_by(name=config.ORGANIZATION_NAME,
                                        tax_id=config.ORGANIZATION_TAX_ID).one()
    assert isinstance(Organization.get_default_org_id(), UUID)
