from datetime import datetime, timedelta
from uuid import uuid4

from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.models import Microtower, Device
from ereuse_devicehub.resources.event.models import Snapshot, SoftwareType, Appearance, \
    Functionality, Bios, SnapshotRequest, TestHardDrive, StressTest
from ereuse_devicehub.resources.user.model import User


# noinspection PyArgumentList
def test_event_model(app: Devicehub):
    """
    Tests creating a Snapshot with its relationships ensuring correct
    DB mapping.
    """
    with app.test_request_context():
        user = User(email='foo@bar.com')
        device = Microtower(serial_number='a1')
        snapshot = Snapshot(uuid=uuid4(),
                            date=datetime.now(),
                            version='1.0',
                            snapshot_software=SoftwareType.DesktopApp,
                            appearance=Appearance.A,
                            appearance_score=5,
                            functionality=Functionality.A,
                            functionality_score=5,
                            labelling=False,
                            bios=Bios.C,
                            condition=5,
                            elapsed=timedelta(seconds=25))
        snapshot.device = device
        snapshot.author = user
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

