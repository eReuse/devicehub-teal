from decimal import Decimal
from distutils.version import StrictVersion

import math
import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import Action, BenchmarkDataStorage, \
    BenchmarkProcessor, RateComputer, Snapshot, VisualTest
from ereuse_devicehub.resources.device.models import Computer, Desktop, Device, HardDrive, \
    Processor, RamModule, SolidStateDrive
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


# TODO JN is necessary this test if in test multiples rates we are checking same case??
def test_rate_with_multiple_visual_tests(user: UserClient):
    """Perform a ComputerRate and then update the device with a new VisualTest.

    Devicehub must make the final rate with the first computer rate
    plus the new visual test, without considering the appearance /
    functionality values of the computer rate.
    """
    s = file('real-hp.snapshot.11')
    snapshot, _ = user.post(s, res=Snapshot)
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    visual_test = next(e for e in reversed(device['actions']) if e['type'] == VisualTest.t)

    assert visual_test['appearanceRange'] == 'B'
    assert visual_test['functionalityRange'] == 'D'
    assert device['rate']['rating'] == 2

    # Adding new visual test
    user.post({
        'type': 'VisualTest',
        'device': device['id'],
        'appearanceRange': 'A',
        'functionalityRange': 'A'
    }, res=Action)
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    visual_test = next(e for e in reversed(device['actions']) if e['type'] == VisualTest.t)

    assert visual_test['appearanceRange'] == 'A'
    assert visual_test['functionalityRange'] == 'A'
    assert device['rate']['rating'] == 3.7


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
    _, price = RateComputer.compute(pc)

    assert price.price == Decimal('92.2001')
    assert price.retailer.standard.amount == Decimal('40.9714')
    assert price.platform.standard.amount == Decimal('18.8434')
    assert price.refurbisher.standard.amount == Decimal('32.3853')
    assert price.price >= price.retailer.standard.amount + price.platform.standard.amount \
           + price.refurbisher.standard.amount
    assert price.retailer.warranty2.amount == Decimal('55.3085')
    assert price.platform.warranty2.amount == Decimal('25.4357')
    assert price.refurbisher.warranty2.amount == Decimal('43.7259')
    assert price.warranty2 == Decimal('124.47')


def test_when_rate_must_not_compute(user: UserClient):
    """
    Test to check if rate is computed in case of should not be calculated:
        1. Snapshot haven't visual test
        2. Snapshot software aren't Workbench
        3. Device type are not Computer
        ...
    """
    # Checking case 1
    s = file('basic.snapshot')
    # Delete snapshot device actions to delete VisualTest
    del s['device']['actions']

    # Post to compute rate and check to didn't do it
    snapshot, _ = user.post(s, res=Snapshot)
    assert 'rate' not in snapshot['device']

    # Checking case 2
    s = file('basic.snapshot')
    # Change snapshot software source
    s['software'] = 'Web'
    del s['uuid']
    del s['elapsed']
    del s['components']

    # Post to compute rate and check to didn't do it
    snapshot, _ = user.post(s, res=Snapshot)
    assert 'rate' not in snapshot['device']

    # Checking case 3
    s = file('keyboard.snapshot')

    # Post to compute rate and check to didn't do it
    snapshot, _ = user.post(s, res=Snapshot)
    assert 'rate' not in snapshot['device']


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_multiple_rates(user: UserClient):
    """Tests submitting two rates from Workbench,
    ensuring that the tests / benchmarks...
    from the first rate do not contaminate the second rate.

    This ensures that rates only takes the last version  of actions
    and components (in case device has new components, for example).
    """
    pc = Desktop(chassis=ComputerChassis.Tower)
    hdd = HardDrive(size=476940)
    hdd.actions_one.add(BenchmarkDataStorage(read_speed=126, write_speed=29.8))
    cpu = Processor(cores=2, speed=3.4)
    cpu.actions_one.add(BenchmarkProcessor(rate=27136.44))
    pc.components = {
        hdd,
        RamModule(size=4096, speed=1600),
        RamModule(size=2048, speed=1600),
        cpu
    }

    # Add test visual with functionality and appearance range
    VisualTest(appearance_range=AppearanceRange.A,
               functionality_range=FunctionalityRange.A,
               device=pc)

    rate1, price1 = RateComputer.compute(pc)

    # asserts rate1 ...
    # TODO JN is also necessary add asserts for component_range??
    assert rate1.data_storage == 4.02
    assert rate1.processor == 3.95
    assert rate1.ram == 3.8

    assert rate1.appearance == 0.3
    assert rate1.functionality == 0.4

    assert rate1.rating == 4.62
    # assert rate1.rating_range == 'High'

    # TODO JN better option to get and assert price??
    assert price1.price == Decimal('92.4001')
    assert math.isclose(rate1.price.price, 92.40, rel_tol=0.001)

    hdd = SolidStateDrive(size=476940)
    hdd.actions_one.add(BenchmarkDataStorage(read_speed=222, write_speed=169))
    cpu = Processor(cores=1, speed=3.0)
    cpu.actions_one.add(BenchmarkProcessor(rate=16069.44))
    # TODO JN best form to update pc components/benchmarks??
    pc.components = {
        hdd,
        RamModule(size=2048, speed=1067),
        RamModule(size=2048, speed=1067),
        cpu
    }

    # Add test visual with functionality and appearance range
    VisualTest(appearance_range=AppearanceRange.B,
               functionality_range=FunctionalityRange.B,
               device=pc)

    # asserts pc characteristics/benchmarks/tests change

    rate2, price2 = RateComputer.compute(pc)

    # asserts rate2 ...

    assert rate2.data_storage == 4.27
    assert rate2.processor == 3.61
    assert rate2.ram == 4.12

    assert rate2.appearance == 0
    assert rate2.functionality == -0.5

    assert rate2.rating == 3.37
    # assert rate2.rating_range == 'Medium'

    assert rate2.price.price == Decimal('67.4001')
    assert math.isclose(price2.price, 67.40, rel_tol=0.001)
