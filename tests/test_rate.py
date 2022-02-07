from decimal import Decimal
from distutils.version import StrictVersion

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
from tests.conftest import file, yaml2json, json_encode


@pytest.mark.mvp
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


@pytest.mark.xfail(reason='Rate algorithm v1 have the limitation of not '
                          'recompute rate when post new visual test')
def test_rate_with_multiple_visual_tests(user: UserClient):
    """Perform a ComputerRate and then update the device with a new VisualTest.

    Devicehub must make the final rate with the first computer rate
    plus the new visual test, without considering the appearance /
    functionality values of the computer rate.
    """
    s = file('real-hp.snapshot.11')
    snapshot, _ = user.post(s, res=Snapshot)
    device, _ = user.get(res=Device, item=snapshot['device']['devicehubID'])
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
    device, _ = user.get(res=Device, item=snapshot['device']['devicehubID'])
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

    assert price.price == Decimal('78.2001')
    assert price.retailer.standard.amount == Decimal('34.7502')
    assert price.platform.standard.amount == Decimal('15.9821')
    assert price.refurbisher.standard.amount == Decimal('27.4678')
    assert price.price >= price.retailer.standard.amount + price.platform.standard.amount \
           + price.refurbisher.standard.amount
    assert price.retailer.warranty2.amount == Decimal('46.9103')
    assert price.platform.warranty2.amount == Decimal('21.5735')
    assert price.refurbisher.warranty2.amount == Decimal('37.0864')
    assert price.warranty2 == Decimal('105.57')


@pytest.mark.mvp
def test_when_rate_must_not_compute(user: UserClient):
    """Test to check if rate is computed in case of should not be calculated:
        1. Snapshot haven't visual test
        2. Snapshot software aren't Workbench
        3. Device type are not Computer
        ...
    """
    # Checking case 1
    s = yaml2json('basic.snapshot')
    # Delete snapshot device actions to delete VisualTest
    del s['device']['actions']

    # Post to compute rate and check to didn't do it
    snapshot, _ = user.post(json_encode(s), res=Snapshot)
    assert 'rate' not in snapshot['device']

    # Checking case 2
    s = yaml2json('basic.snapshot')
    # Change snapshot software source
    s['software'] = 'Web'
    del s['uuid']
    del s['elapsed']
    del s['components']

    # Post to compute rate and check to didn't do it
    snapshot, _ = user.post(json_encode(s), res=Snapshot)
    assert 'rate' not in snapshot['device']

    # Checking case 3
    s = yaml2json('keyboard.snapshot')

    # Post to compute rate and check to didn't do it
    snapshot, _ = user.post(json_encode(s), res=Snapshot)
    assert 'rate' not in snapshot['device']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_multiple_rates(user: UserClient):
    """Tests submitting two rates from Workbench,
    ensuring that the tests / benchmarks...
    from the first rate do not contaminate the second rate.

    This ensures that rates only takes all the correct actions
    and components rates in case device have new tests/benchmarks.
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
    assert rate1.data_storage == 4.02
    assert rate1.processor == 3.95
    assert rate1.ram == 3.8

    assert rate1.appearance is None
    assert rate1.functionality is None

    assert rate1.rating == 3.92

    assert price1.price == Decimal('78.4001')

    cpu.actions_one.add(BenchmarkProcessor(rate=16069.44))
    ssd = SolidStateDrive(size=476940)
    ssd.actions_one.add(BenchmarkDataStorage(read_speed=222, write_speed=111))
    pc.components |= {
        ssd,
        RamModule(size=2048, speed=1067),
        RamModule(size=2048, speed=1067),
    }

    # Add test visual with functionality and appearance range
    VisualTest(appearance_range=AppearanceRange.B,
               functionality_range=FunctionalityRange.B,
               device=pc)

    rate2, price2 = RateComputer.compute(pc)

    assert rate2.data_storage == 4.3
    assert rate2.processor == 3.78
    assert rate2.ram == 3.95

    assert rate2.appearance is None
    assert rate2.functionality is None

    assert rate2.rating == 3.93

    assert price2.price == Decimal('78.6001')
