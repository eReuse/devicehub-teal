from decimal import Decimal
from distutils.version import StrictVersion

import pytest

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Computer, Desktop, HardDrive, Processor, \
    RamModule
from ereuse_devicehub.resources.enums import AppearanceRange, ComputerChassis, \
    FunctionalityRange
from ereuse_devicehub.resources.event.models import BenchmarkDataStorage, \
    BenchmarkProcessor, EreusePrice, RateComputer, TestVisual
from tests import conftest


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_workbench_rate_db():
    rate = RateComputer(processor=0.1,
                        ram=1.0,
                        labelling=False,
                        graphic_card=0.1,
                        data_storage=4.1,
                        version=StrictVersion('1.0'),
                        device=Computer(serial_number='24', chassis=ComputerChassis.Tower))
    db.session.add(rate)
    db.session.commit()


@pytest.mark.xfail(reason='AggreagteRate only takes data from WorkbenchRate as for now')
def test_rate_workbench_then_manual():
    """Checks that a new Rate is generated with a new rate
    value when a TestVisual is performed after performing a
    RateComputer.

    The new Rate needs to be computed by the values of
    the appearance and funcitonality grade of TestVisual.
    """
    pass


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate():
    """Test generating an Rate for a given PC / components /
    RateComputer ensuring results and relationships between
    pc - rate - RateComputer - price.
    """
    rate = RateComputer()
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
    visual_test = TestVisual()
    visual_test.appearance_range = AppearanceRange.A
    visual_test.functionality_range = FunctionalityRange.A

    pc.events_one.add(visual_test)
    # TODO why events_one?? how to rewrite correctly this tests??
    events = rate.compute(pc)
    price = next(e for e in events if isinstance(e, EreusePrice))
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
    # TODO How to check new relationships??
    # Checks relationships
    rate_computer = next(e for e in events if isinstance(e, RateComputer))
    assert rate_computer.rating == 4.61
