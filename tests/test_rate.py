from decimal import Decimal
from distutils.version import StrictVersion

import pytest

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Computer, Desktop, HardDrive, Processor, \
    RamModule
from ereuse_devicehub.resources.enums import AppearanceRange, Bios, ComputerChassis, \
    FunctionalityRange, RatingSoftware
from ereuse_devicehub.resources.event.models import AggregateRate, BenchmarkDataStorage, \
    BenchmarkProcessor, EreusePrice, WorkbenchRate
from ereuse_devicehub.resources.event.rate import main
from tests import conftest


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_workbench_rate_db():
    rate = WorkbenchRate(processor=0.1,
                         ram=1.0,
                         bios_range=Bios.A,
                         labelling=False,
                         graphic_card=0.1,
                         data_storage=4.1,
                         software=RatingSoftware.ECost,
                         version=StrictVersion('1.0'),
                         device=Computer(serial_number='24', chassis=ComputerChassis.Tower))
    db.session.add(rate)
    db.session.commit()


@pytest.mark.xfail(reason='AggreagteRate only takes data from WorkbenchRate as for now')
def test_rate_workbench_then_manual():
    """Checks that a new AggregateRate is generated with a new rate
    value when a ManualRate is performed after performing a
    WorkbenchRate.

    The new AggregateRate needs to be computed by the values of
    the WorkbenchRate + new values from ManualRate.
    """
    pass


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate():
    """Test generating an AggregateRate for a given PC / components /
    WorkbenchRate ensuring results and relationships between
    pc - rate - workbenchRate - price.
    """
    rate = WorkbenchRate(
        appearance_range=AppearanceRange.A,
        functionality_range=FunctionalityRange.A
    )
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
    rate.device = pc
    events = main.main(rate, RatingSoftware.ECost, StrictVersion('1.0'))
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
    # Checks relationships
    workbench_rate = next(e for e in events if isinstance(e, WorkbenchRate))
    aggregate_rate = next(e for e in events if isinstance(e, AggregateRate))
    assert price.rating == aggregate_rate
    assert aggregate_rate.workbench == workbench_rate
    assert aggregate_rate.rating == workbench_rate.rating == 4.61
    assert aggregate_rate.software == workbench_rate.software == RatingSoftware.ECost
    assert aggregate_rate.version == StrictVersion('1.0')
    assert aggregate_rate.appearance == workbench_rate.appearance
    assert aggregate_rate.functionality == workbench_rate.functionality
    assert aggregate_rate.rating_range == workbench_rate.rating_range
    assert cpu.rate == pc.rate == hdd.rate == aggregate_rate
    assert cpu.price == pc.price == aggregate_rate.price == hdd.price == price
