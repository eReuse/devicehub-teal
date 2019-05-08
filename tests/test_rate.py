from decimal import Decimal
from distutils.version import StrictVersion

import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Computer, Desktop, HardDrive, Processor, \
    RamModule
from ereuse_devicehub.resources.enums import AppearanceRange, ComputerChassis, \
    FunctionalityRange
from ereuse_devicehub.resources.event.models import BenchmarkDataStorage, BenchmarkProcessor, \
    RateComputer, Snapshot, VisualTest
from ereuse_devicehub.resources.event.rate.workbench.v1_0 import CannotRate
from tests import conftest
from tests.conftest import file


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_workbench_rate_db():
    rate = RateComputer(processor=0.1,
                        ram=1.0,
                        data_storage=4.1,
                        graphic_card=0.1,
                        version=StrictVersion('1.0'),
                        device=Computer(serial_number='24', chassis=ComputerChassis.Tower))
    db.session.add(rate)
    db.session.commit()


@pytest.mark.xfail(reason='ComputerRate V1 can only be triggered from Workbench snapshot software')
def test_rate_workbench_then_manual():
    """Checks that a new Rate is generated for a snapshot
    that is not from Workbench.
    """


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate():
    """Test generating an Rate for a given PC / components /
    RateComputer ensuring results and relationships between
    pc - rate - RateComputer - price.
    """

    pc = Desktop(chassis=ComputerChassis.Tower)
    hdd = HardDrive(size=476940)
    hdd.events_one.add(BenchmarkDataStorage(read_speed=126, write_speed=29.8))
    cpu = Processor(cores=2, speed=3.4)
    cpu.events_one.add(BenchmarkProcessor(rate=27136.44))
    pc.components |= {
        hdd,
        RamModule(size=4096, speed=1600),
        RamModule(size=2048, speed=1067),
        cpu
    }

    # Add test visual with functionality and appearance range
    VisualTest(appearance_range=AppearanceRange.A,
               functionality_range=FunctionalityRange.A,
               device=pc)
    rate, price = RateComputer.compute(pc)

    # events = pc.events
    # price = next(e for e in events if isinstance(e, EreusePrice))
    assert price.price == Decimal('92.2001')
    assert price.retailer.standard.amount == Decimal('40.9714')
    assert price.platform.standard.amount == Decimal('18.8434')
    assert price.refurbisher.standard.amount == Decimal('32.3853')
    assert price.price >= price.retailer.standard.amount \
           + price.platform.standard.amount \
           + price.refurbisher.standard.amount
    assert price.retailer.warranty2.amount == Decimal('55.3085')
    assert price.platform.warranty2.amount == Decimal('25.4357')
    assert price.refurbisher.warranty2.amount == Decimal('43.7259')
    assert price.warranty2 == Decimal('124.47')


def test_no_rate_if_no_workbench(user: UserClient):
    """
    Checks if compute a rate from snapshot software is not from Workbench
    """
    # Upload a basic snapshot
    device_no_wb = file('basic.snapshot')
    # Change snapshot software source
    device_no_wb['software'] = 'Web'
    del device_no_wb['uuid']
    del device_no_wb['elapsed']
    del device_no_wb['components']
    # Try to compute rate
    user.post(device_no_wb, res=Snapshot)
    # How to assert CannotRate Exception
    assert CannotRate


def test_no_rate_if_no_visual_test(user: UserClient):
    """
    Checks if a rate is calculated from a snapshot without visual test
    """
    # Upload a basic snapshot
    device = file('basic.snapshot')
    # Delete snapshot device events
    del device['device']['events']
    user.post(device, res=Snapshot)
    # How to assert CannotRate Exception
    assert CannotRate


def test_no_rate_if_device_is_not_computer(user: UserClient):
    """
    Checks if a rate is calculated from a device that is not a computer.
    """
    # Upload a basic snapshot of a device type
    device = file('keyboard.snapshot')
    user.post(device, res=Snapshot)
    assert CannotRate


@pytest.mark.xfail(reason='Test not developed')
def test_multiple_rates(user: UserClient):
    """Tests submitting two rates from Workbench,
    ensuring that the tests / benchmarks...
    from the first rate do not contaminate the second rate.

    This ensures that rates only takes the last version  of events
    and components (in case device has new components, for example).
    """
