from datetime import datetime, timedelta

import pytest
from flask import g

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device, GraphicCard, HardDrive, \
    SolidStateDrive
from ereuse_devicehub.resources.enums import TestHardDriveLength
from ereuse_devicehub.resources.event.models import EraseBasic, EraseSectors, \
    EventWithOneDevice, Install, StepZero, TestDataStorage
from tests.conftest import create_user


@pytest.mark.usefixtures('app_context')
def test_author():
    """
    Checks the default created author.

    Note that the author can be accessed after inserting the row.
    """
    user = create_user()
    g.user = user
    e = EventWithOneDevice(device=Device())
    db.session.add(e)
    assert e.author is None
    assert e.author_id is None
    db.session.commit()
    assert e.author == user


@pytest.mark.usefixtures('auth_app_context')
def test_erase_basic():
    erasure = EraseBasic(
        device=HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        clean_with_zeros=True,
        start_time=datetime.now(),
        end_time=datetime.now(),
        secure_random_steps=25,
        error=False
    )
    db.session.add(erasure)
    db.session.commit()
    db_erasure = EraseBasic.query.one()
    assert erasure == db_erasure
    assert next(iter(db_erasure.device.events)) == erasure


@pytest.mark.usefixtures('auth_app_context')
def test_validate_device_data_storage():
    """Checks the validation for data-storage-only events works."""
    # We can't set a GraphicCard
    with pytest.raises(TypeError,
                       message='EraseBasic.device must be a DataStorage '
                               'but you passed <GraphicCard None model=\'foo-bar\' S/N=\'foo\'>'):
        EraseBasic(
            device=GraphicCard(serial_number='foo', manufacturer='bar', model='foo-bar'),
            clean_with_zeros=True,
            start_time=datetime.now(),
            end_time=datetime.now(),
            secure_random_steps=25,
            error=False
        )


@pytest.mark.usefixtures('auth_app_context')
def test_erase_sectors_steps():
    erasure = EraseSectors(
        device=SolidStateDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        clean_with_zeros=True,
        start_time=datetime.now(),
        end_time=datetime.now(),
        secure_random_steps=25,
        error=False,
        steps=[
            StepZero(error=False,
                     start_time=datetime.now(),
                     end_time=datetime.now(),
                     secure_random_steps=1,
                     clean_with_zeros=True),
            StepZero(error=False,
                     start_time=datetime.now(),
                     end_time=datetime.now(),
                     secure_random_steps=2,
                     clean_with_zeros=True),
            StepZero(error=False,
                     start_time=datetime.now(),
                     end_time=datetime.now(),
                     secure_random_steps=3,
                     clean_with_zeros=True)
        ]
    )
    db.session.add(erasure)
    db.session.commit()
    db_erasure = EraseSectors.query.one()
    # Steps are in order
    assert db_erasure.steps[0].secure_random_steps == 1
    assert db_erasure.steps[0].num == 0
    assert db_erasure.steps[1].secure_random_steps == 2
    assert db_erasure.steps[1].num == 1
    assert db_erasure.steps[2].secure_random_steps == 3
    assert db_erasure.steps[2].num == 2


@pytest.mark.usefixtures('auth_app_context')
def test_test_data_storage():
    test = TestDataStorage(
        device=HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        error=False,
        elapsed=timedelta(minutes=25),
        length=TestHardDriveLength.Short,
        status='OK!',
        lifetime=timedelta(days=120)
    )
    db.session.add(test)
    db.session.commit()
    assert TestDataStorage.query.one()


@pytest.mark.usefixtures('auth_app_context')
def test_install():
    hdd = HardDrive(serial_number='sn')
    install = Install(name='LinuxMint 18.04 es',
                      elapsed=timedelta(seconds=25),
                      device=hdd)
    db.session.add(install)
    db.session.commit()
