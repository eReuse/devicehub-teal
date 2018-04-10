from datetime import datetime, timedelta
from uuid import uuid4

from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.models import Desktop, NetworkAdapter
from ereuse_devicehub.resources.event.models import Snapshot, SoftwareType, Appearance, \
    Functionality, Bios
from ereuse_devicehub.resources.user.model import User


# noinspection PyArgumentList
def test_init(app: Devicehub):
    """Tests app initialization."""
    pass
