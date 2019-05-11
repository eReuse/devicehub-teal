from decimal import Decimal
from distutils.version import StrictVersion

import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import Action, BenchmarkDataStorage, \
    BenchmarkProcessor, RateComputer, Snapshot, VisualTest
from ereuse_devicehub.resources.action.rate.workbench.v1_0 import CannotRate
from ereuse_devicehub.resources.device.models import Computer, Desktop, Device, HardDrive, \
    Processor, RamModule
from ereuse_devicehub.resources.enums import AppearanceRange, ComputerChassis, \
    FunctionalityRange
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


@pytest.mark.xfail(reson='Adapt rate algorithm to re-compute by passing a manual rate.')
def test_manual_rate_after_workbench_rate(user: UserClient):
    """Perform a WorkbenchRate and then update the device with a ManualRate.

    Devicehub must make the final rate with the first workbench rate
    plus the new manual rate, without considering the appearance /
    functionality values of the workbench rate.
    """
    s = file('real-hp.snapshot.11')
    snapshot, _ = user.post(s, res=Snapshot)
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert 'B' == device['rate']['appearanceRange']
    assert device['rate'] == 1
    user.post({
        'type': 'ManualRate',
        'device': device['id'],
        'appearanceRange': 'A',
        'functionalityRange': 'A'
    }, res=Action)
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert 'A' == device['rate']['appearanceRange']


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_price_from_rate():
    """Tests the price generated from the rate."""

    pc = Desktop(chassis=ComputerChassis.Tower)
    hdd = HardDrive(size=476940)
    hdd.actions_one.add(BenchmarkDataStorage(read_speed=126, write_speed=29.8))
    cpu = Processor(cores=2, speed=3.4)
    cpu.actions_one.add(BenchmarkProcessor(rate=27136.44))
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

    # actions = pc.actions
    # price = next(e for e in actions if isinstance(e, EreusePrice))
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
    s = file('basic.snapshot')
    # Delete snapshot device actions
    del s['device']['actions']
    snapshot, _ = user.post(s, res=Snapshot)
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    # How to assert CannotRate Exception
    assert 'rate' not in snapshot['device']


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

    This ensures that rates only takes the last version  of actions
    and components (in case device has new components, for example).
    """
