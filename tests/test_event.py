from datetime import datetime, timedelta

import pytest
from flask import g
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Desktop, Device, GraphicCard, HardDrive, \
    RamModule, SolidStateDrive
from ereuse_devicehub.resources.enums import TestHardDriveLength
from ereuse_devicehub.resources.event import models
from tests.conftest import create_user, file


@pytest.mark.usefixtures('app_context')
def test_author():
    """
    Checks the default created author.

    Note that the author can be accessed after inserting the row.
    """
    user = create_user()
    g.user = user
    e = models.EventWithOneDevice(device=Device())
    db.session.add(e)
    assert e.author is None
    assert e.author_id is None
    db.session.commit()
    assert e.author == user


@pytest.mark.usefixtures('auth_app_context')
def test_erase_basic():
    erasure = models.EraseBasic(
        device=HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        zeros=True,
        start_time=datetime.now(),
        end_time=datetime.now(),
        error=False
    )
    db.session.add(erasure)
    db.session.commit()
    db_erasure = models.EraseBasic.query.one()
    assert erasure == db_erasure
    assert next(iter(db_erasure.device.events)) == erasure


@pytest.mark.usefixtures('auth_app_context')
def test_validate_device_data_storage():
    """Checks the validation for data-storage-only events works."""
    # We can't set a GraphicCard
    with pytest.raises(TypeError,
                       message='EraseBasic.device must be a DataStorage '
                               'but you passed <GraphicCard None model=\'foo-bar\' S/N=\'foo\'>'):
        models.EraseBasic(
            device=GraphicCard(serial_number='foo', manufacturer='bar', model='foo-bar'),
            clean_with_zeros=True,
            start_time=datetime.now(),
            end_time=datetime.now(),
            error=False
        )


@pytest.mark.usefixtures('auth_app_context')
def test_erase_sectors_steps():
    erasure = models.EraseSectors(
        device=SolidStateDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        zeros=True,
        start_time=datetime.now(),
        end_time=datetime.now(),
        error=False,
        steps=[
            models.StepZero(error=False,
                            start_time=datetime.now(),
                            end_time=datetime.now()),
            models.StepRandom(error=False,
                              start_time=datetime.now(),
                              end_time=datetime.now()),
            models.StepZero(error=False,
                            start_time=datetime.now(),
                            end_time=datetime.now())
        ]
    )
    db.session.add(erasure)
    db.session.commit()
    db_erasure = models.EraseSectors.query.one()
    # Steps are in order
    assert db_erasure.steps[0].num == 0
    assert db_erasure.steps[1].num == 1
    assert db_erasure.steps[2].num == 2


@pytest.mark.usefixtures('auth_app_context')
def test_test_data_storage():
    test = models.TestDataStorage(
        device=HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        error=False,
        elapsed=timedelta(minutes=25),
        length=TestHardDriveLength.Short,
        status='OK!',
        lifetime=timedelta(days=120)
    )
    db.session.add(test)
    db.session.commit()
    assert models.TestDataStorage.query.one()


@pytest.mark.usefixtures('auth_app_context')
def test_install():
    hdd = HardDrive(serial_number='sn')
    install = models.Install(name='LinuxMint 18.04 es',
                             elapsed=timedelta(seconds=25),
                             device=hdd)
    db.session.add(install)
    db.session.commit()


@pytest.mark.usefixtures('auth_app_context')
def test_update_components_event_one():
    computer = Desktop(serial_number='sn1', model='ml1', manufacturer='mr1')
    hdd = HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar')
    computer.components.add(hdd)

    # Add event
    test = models.StressTest(elapsed=timedelta(seconds=1))
    computer.events_one.add(test)
    assert test.device == computer
    assert next(iter(test.components)) == hdd, 'Event has to have new components'

    # Remove event
    computer.events_one.clear()
    assert not test.device
    assert not test.components, 'Event has to loose the components'

    # If we add a component to a device AFTER assigning the event
    # to the device, the event doesn't get the new component
    computer.events_one.add(test)
    ram = RamModule()
    computer.components.add(ram)
    assert len(test.components) == 1


@pytest.mark.usefixtures('auth_app_context')
def test_update_components_event_multiple():
    computer = Desktop(serial_number='sn1', model='ml1', manufacturer='mr1')
    hdd = HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar')
    computer.components.add(hdd)

    ready = models.Ready()
    assert not ready.devices
    assert not ready.components

    # Add
    computer.events_multiple.add(ready)
    assert ready.devices == OrderedSet([computer])
    assert next(iter(ready.components)) == hdd

    # Remove
    computer.events_multiple.remove(ready)
    assert not ready.devices
    assert not ready.components

    # init / replace collection
    ready.devices = OrderedSet([computer])
    assert ready.devices
    assert ready.components


@pytest.mark.usefixtures('auth_app_context')
def test_update_parent():
    computer = Desktop(serial_number='sn1', model='ml1', manufacturer='mr1')
    hdd = HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar')
    computer.components.add(hdd)

    # Add
    benchmark = models.BenchmarkDataStorage()
    benchmark.device = hdd
    assert benchmark.parent == computer
    assert not benchmark.components

    # Remove
    benchmark.device = None
    assert not benchmark.parent


@pytest.mark.xfail(reason='No POST view for generic tests')
@pytest.mark.parametrize('event_model', [
    models.ToRepair,
    models.Repair,
    models.ToPrepare,
    models.Prepare,
    models.ToDispose,
    models.Dispose,
    models.Ready
])
def test_generic_event(event_model: models.Event, user: UserClient):
    """Tests POSTing all generic events."""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    event = {'type': event_model.t, 'devices': [snapshot['device']['id']]}
    event, _ = user.post(event, res=event_model)
    assert event['device'][0]['id'] == snapshot['device']['id']
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert device['events'][0]['id'] == event['id']
