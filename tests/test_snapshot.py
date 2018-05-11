from datetime import datetime, timedelta
from typing import List
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


def assert_similar_device(device1: dict, device2: dict):
    """
    Like Model.is_similar() but adapted for testing.
    """
    assert isinstance(device1, dict) and device1
    assert isinstance(device2, dict) and device2
    for key in 'serialNumber', 'model', 'manufacturer', 'type':
        assert device1.get(key, None) == device2.get(key, None)


def assert_similar_components(components1: List[dict], components2: List[dict]):
    """
    Asserts that the components in components1 are
    similar than the components in components2.
    """
    assert len(components1) == len(components2)
    for c1, c2 in zip(components1, components2):
        assert_similar_device(c1, c2)


def snapshot_and_check(user: UserClient,
                       input_snapshot: dict,
                       num_events: int = 0,
                       perform_second_snapshot=True) -> dict:
    """

    """
    snapshot, _ = user.post(res=Snapshot, data=input_snapshot)
    assert len(snapshot['events']) == num_events
    assert input_snapshot['device']
    assert_similar_device(input_snapshot['device'], snapshot['device'])
    assert_similar_components(input_snapshot['components'], snapshot['components'])
    if perform_second_snapshot:
        return snapshot_and_check(user, input_snapshot, num_events, False)
    else:
        return snapshot


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
    """
    Tests the post snapshot endpoint (validation, etc)
    and data correctness.
    """
    snapshot = snapshot_and_check(user, file('basic.snapshot'))
    assert snapshot['software'] == 'Workbench'
    assert snapshot['version'] == '11.0'
    assert snapshot['uuid'] == 'f5efd26e-8754-46bc-87bf-fbccc39d60d9'
    assert snapshot['events'] == []
    assert snapshot['elapsed'] == 4
    assert snapshot['author']['id'] == user.user['id']
    assert 'events' not in snapshot['device']
    assert 'author' not in snapshot['device']


def test_snapshot_add_remove(user: UserClient):
    s1 = file('1-device-with-components.snapshot')
    snapshot_and_check(user, s1)

    s2 = file('2-second-device-with-components-of-first.snapshot')
    s3 = file('3-first-device-but-removing-motherboard-and-adding-processor-from-2.snapshot')
    s4 = file('4-first-device-but-removing-processor.snapshot-and-adding-graphic-card')
