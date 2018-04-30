from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.models import Device, Microtower
from ereuse_devicehub.resources.event.models import Appearance, Bios, Functionality, Snapshot, \
    SnapshotRequest, SoftwareType
from ereuse_devicehub.resources.user.models import User
from tests.conftest import file


@pytest.mark.usefixtures('auth_app_context')
def test_snapshot_model():
    """
    Tests creating a Snapshot with its relationships ensuring correct
    DB mapping.
    """
    device = Microtower(serial_number='a1')
    # noinspection PyArgumentList
    snapshot = Snapshot(uuid=uuid4(),
                        date=datetime.now(),
                        version='1.0',
                        software=SoftwareType.DesktopApp,
                        appearance=Appearance.A,
                        appearance_score=5,
                        functionality=Functionality.A,
                        functionality_score=5,
                        labelling=False,
                        bios=Bios.C,
                        condition=5,
                        elapsed=timedelta(seconds=25))
    snapshot.device = device
    snapshot.request = SnapshotRequest(request={'foo': 'bar'})

    db.session.add(snapshot)
    db.session.commit()
    device = Microtower.query.one()  # type: Microtower
    assert device.events_one[0].type == Snapshot.__name__
    db.session.delete(device)
    db.session.commit()
    assert Snapshot.query.one_or_none() is None
    assert SnapshotRequest.query.one_or_none() is None
    assert User.query.one() is not None
    assert Microtower.query.one_or_none() is None
    assert Device.query.one_or_none() is None


def test_snapshot_schema(app: Devicehub):
    with app.app_context():
        s = file('basic.snapshot')
        app.resources['Snapshot'].schema.load(s)


def test_snapshot_post(user: UserClient):
    """Tests the post snapshot endpoint (validation, etc)."""
    s = file('basic.snapshot')
    snapshot, _ = user.post(s, res=Snapshot.__name__)
