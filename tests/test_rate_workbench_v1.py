"""
Tests of compute rating for every component in a Device
Rates test done:
        -DataStorage
        -RamModule
        -Processor

Excluded cases in tests

- No Processor
-

"""

import pytest

from ereuse_devicehub.resources.device.models import Desktop, HardDrive, Processor, RamModule
from ereuse_devicehub.resources.enums import AppearanceRange, ComputerChassis, FunctionalityRange
from ereuse_devicehub.resources.event.models import BenchmarkDataStorage, BenchmarkProcessor, \
    WorkbenchRate
from ereuse_devicehub.resources.event.rate.workbench.v1_0 import DataStorageRate, ProcessorRate, \
    RamRate, Rate


def test_rate_data_storage_rate():
    """
    Test to check if compute data storage rate have same value than previous score version;
    id = pc_1193, pc_1201, pc_79, pc_798
    """

    hdd_1969 = HardDrive(size=476940)
    hdd_1969.events_one.add(BenchmarkDataStorage(read_speed=126, write_speed=29.8))

    data_storage_rate = DataStorageRate().compute([hdd_1969], WorkbenchRate())

    assert round(data_storage_rate, 2) == 4.02, 'DataStorageRate returns incorrect value(rate)'

    hdd_3054 = HardDrive(size=476940)
    hdd_3054.events_one.add(BenchmarkDataStorage(read_speed=158, write_speed=34.7))

    # calculate DataStorage Rate
    data_storage_rate = DataStorageRate().compute([hdd_3054], WorkbenchRate())

    assert round(data_storage_rate, 2) == 4.07, 'DataStorageRate returns incorrect value(rate)'

    hdd_81 = HardDrive(size=76319)
    hdd_81.events_one.add(BenchmarkDataStorage(read_speed=72.2, write_speed=24.3))

    data_storage_rate = DataStorageRate().compute([hdd_81], WorkbenchRate())

    assert round(data_storage_rate, 2) == 2.61, 'DataStorageRate returns incorrect value(rate)'

    hdd_1556 = HardDrive(size=152587)
    hdd_1556.events_one.add(BenchmarkDataStorage(read_speed=78.1, write_speed=24.4))

    data_storage_rate = DataStorageRate().compute([hdd_1556], WorkbenchRate())

    assert round(data_storage_rate, 2) == 3.70, 'DataStorageRate returns incorrect value(rate)'


def test_rate_data_storage_size_is_null():
    """
    Test where input DataStorage.size = NULL, BenchmarkDataStorage.read_speed = 0,
    BenchmarkDataStorage.write_speed = 0 is like no DataStorage has been detected;
    id = pc_2992
    """

    hdd_null = HardDrive(size=None)
    hdd_null.events_one.add(BenchmarkDataStorage(read_speed=0, write_speed=0))

    data_storage_rate = DataStorageRate().compute([hdd_null], WorkbenchRate())
    assert data_storage_rate is None


def test_rate_no_data_storage():
    """
    Test without data storage devices
    """
    hdd_null = HardDrive()
    hdd_null.events_one.add(BenchmarkDataStorage(read_speed=0, write_speed=0))
    data_storage_rate = DataStorageRate().compute([hdd_null], WorkbenchRate())
    assert data_storage_rate is None


# RAM MODULE DEVICE TEST


def test_rate_ram_rate():
    """
    Test to check if compute ram rate have same value than previous score version
    only with 1 RamModule; id = pc_1201
    """

    ram1 = RamModule(size=2048, speed=1333)

    ram_rate = RamRate().compute([ram1], WorkbenchRate())

    assert round(ram_rate, 2) == 2.02, 'RamRate returns incorrect value(rate)'


def test_rate_ram_rate_2modules():
    """
    Test to check if compute ram rate have same value than previous score version
    with 2 RamModule; id = pc_1193
    """

    ram1 = RamModule(size=4096, speed=1600)
    ram2 = RamModule(size=2048, speed=1067)

    ram_rate = RamRate().compute([ram1, ram2], WorkbenchRate())

    assert round(ram_rate, 2) == 3.79, 'RamRate returns incorrect value(rate)'


def test_rate_ram_rate_4modules():
    """
    Test to check if compute ram rate have same value than previous score version
    with 2 RamModule; id = pc_79
    """

    ram1 = RamModule(size=512, speed=667)
    ram2 = RamModule(size=512, speed=800)
    ram3 = RamModule(size=512, speed=667)
    ram4 = RamModule(size=512, speed=533)

    ram_rate = RamRate().compute([ram1, ram2, ram3, ram4], WorkbenchRate())

    assert round(ram_rate, 2) == 1.99, 'RamRate returns incorrect value(rate)'


def test_rate_ram_module_size_is_0():
    """
    Test where input data RamModule.size = 0; is like no RamModule has been detected; id =  pc_798
    """

    ram0 = RamModule(size=0, speed=888)

    ram_rate = RamRate().compute([ram0], WorkbenchRate())
    assert ram_rate is None


def test_rate_ram_speed_is_null():
    """
    Test where RamModule.speed is NULL (not detected) but has size.
    Pc ID = 795(1542), 745(1535), 804(1549)
    """

    ram0 = RamModule(size=2048, speed=None)

    ram_rate = RamRate().compute([ram0], WorkbenchRate())

    assert round(ram_rate, 2) == 1.85, 'RamRate returns incorrect value(rate)'

    ram0 = RamModule(size=1024, speed=None)

    ram_rate = RamRate().compute([ram0], WorkbenchRate())

    assert round(ram_rate, 2) == 1.25, 'RamRate returns incorrect value(rate)'


def test_rate_no_ram_module():
    """
    Test without RamModule
    """
    ram0 = RamModule()

    ram_rate = RamRate().compute([ram0], WorkbenchRate())
    assert ram_rate is None


# PROCESSOR DEVICE TEST

def test_rate_processor_rate():
    """
    Test to check if compute processor rate have same value than previous score version
    only with 1 core; id = 79
    """

    cpu = Processor(cores=1, speed=1.6)
    # add score processor benchmark
    cpu.events_one.add(BenchmarkProcessor(rate=3192.34))

    processor_rate = ProcessorRate().compute(cpu, WorkbenchRate())

    assert processor_rate == 1, 'ProcessorRate returns incorrect value(rate)'


def test_rate_processor_rate_2cores():
    """
    Test to check if compute processor rate have same value than previous score version
    with 2 cores; id = pc_1193, pc_1201
    """

    cpu = Processor(cores=2, speed=3.4)
    # add score processor benchmark
    cpu.events_one.add(BenchmarkProcessor(rate=27136.44))

    processor_rate = ProcessorRate().compute(cpu, WorkbenchRate())

    assert round(processor_rate, 2) == 3.95, 'ProcessorRate returns incorrect value(rate)'

    cpu = Processor(cores=2, speed=3.3)
    cpu.events_one.add(BenchmarkProcessor(rate=26339.48))

    processor_rate = ProcessorRate().compute(cpu, WorkbenchRate())

    assert round(processor_rate, 2) == 3.93, 'ProcessorRate returns incorrect value(rate)'


@pytest.mark.xfail(reason='Debug test')
def test_rate_processor_with_null_cores():
    """
    Test with processor device have null number of cores
    """
    cpu = Processor(cores=None, speed=3.3)
    cpu.events_one.add(BenchmarkProcessor(rate=0))

    processor_rate = ProcessorRate().compute(cpu, WorkbenchRate())

    assert processor_rate == 1, 'ProcessorRate returns incorrect value(rate)'


@pytest.mark.xfail(reason='Debug test')
def test_rate_processor_with_null_speed():
    """
    Test with processor device have null speed value
    """
    cpu = Processor(cores=1, speed=None)
    cpu.events_one.add(BenchmarkProcessor(rate=0))

    processor_rate = ProcessorRate().compute(cpu, WorkbenchRate())

    assert processor_rate == 1.06, 'ProcessorRate returns incorrect value(rate)'


def test_rate_computer_rate():
    """ Test rate v1
    
        pc_1193 = Computer()
        price = 92.2
        # add components characteristics of pc with id = 1193
        hdd_1969 = HardDrive(size=476940)
        hdd_1969.events_one.add(BenchmarkDataStorage(read_speed=126, write_speed=29.8))
        ram1 = RamModule(size=4096, speed=1600)
        ram2 = RamModule(size=2048, speed=1067)
        cpu = Processor(cores=2, speed=3.4)
        cpu.events_one.add(BenchmarkProcessor(rate=27136.44))
        pc_1193.components.add(hdd_1969, ram1, ram2, cpu)
        # add functionality and appearance range
        rate_pc_1193 = WorkbenchRate(appearance_range=AppearanceRange.A, functionality_range=FunctionalityRange.A)
        # add component rate
        HDD_rate = 4.02
        RAM_rate = 3.79
        Processor_rate = 3.95
        Rating = 4.61

        pc_1201 = Computer()
        price = 69.6
        hdd_3054 = HardDrive(size=476940)
        hdd_3054.events_one.add(BenchmarkDataStorage(read_speed=158, write_speed=34.7))
        ram1 = RamModule(size=2048, speed=1333)
        cpu = Processor(cores=2, speed=3.3)
        cpu.events_one.add(BenchmarkProcessor(rate=26339.48))
        pc_1201.components.add(hdd_3054, ram1, cpu)
        # add functionality and appearance range
        rate_pc_1201 = WorkbenchRate(appearance_range=AppearanceRange.B, functionality_range=FunctionalityRange.A)
        # add component rate
        HDD_rate = 4.07
        RAM_rate = 2.02
        Processor_rate = 3.93
        Rating = 3.48

        pc_79 = Computer()
        price = VeryLow
        hdd_81 = HardDrive(size=76319)
        hdd_81.events_one.add(BenchmarkDataStorage(read_speed=72.2, write_speed=24.3))
        ram1 = RamModule(size=512, speed=667)
        ram2 = RamModule(size=512, speed=800)
        ram3 = RamModule(size=512, speed=667)
        ram4 = RamModule(size=512, speed=533)
        cpu = Processor(cores=1, speed=1.6)
        cpu.events_one.add(BenchmarkProcessor(rate=3192.34))
        pc_79.components.add(hdd_81, ram1, ram2, ram3, ram4, cpu)
        # add functionality and appearance range
        rate_pc_79 = WorkbenchRate(appearance_range=AppearanceRange.C, functionality_range=FunctionalityRange.A)
        # add component rate
        HDD_rate = 2.61
        RAM_rate = 1.99
        Processor_rate = 1
        Rating = 1.58

        pc_798 = Computer()
        price = 50
        hdd_1556 = HardDrive(size=152587)
        hdd_1556.events_one.add(BenchmarkDataStorage(read_speed=78.1, write_speed=24.4))
        ram0 = RamModule(size=0, speed=None)
        cpu = Processor(cores=2, speed=2.5)
        cpu.events_one.add(BenchmarkProcessor(rate=9974.3))
        pc_798.components.add(hdd_1556, ram0, cpu)
        # add functionality and appearance range
        rate_pc_798 = WorkbenchRate(appearance_range=AppearanceRange.B, functionality_range=FunctionalityRange.A)
        # add component rate
        HDD_rate = 3.7
        RAM_rate = 1
        Processor_rate = 4.09
        Rating = 2.5
    """

    # Create a new Computer with components characteristics of pc with id = 1193
    pc_test = Desktop(chassis=ComputerChassis.Tower)
    data_storage = HardDrive(size=476940)
    data_storage.events_one.add(BenchmarkDataStorage(read_speed=126, write_speed=29.8))
    cpu = Processor(cores=2, speed=3.4)
    cpu.events_one.add(BenchmarkProcessor(rate=27136.44))
    pc_test.components |= {
        data_storage,
        RamModule(size=4096, speed=1600),
        RamModule(size=2048, speed=1067),
        cpu
    }
    # add functionality and appearance range
    rate_pc = WorkbenchRate(appearance_range=AppearanceRange.A,
                            functionality_range=FunctionalityRange.A)
    # Compute all components rates and general rating
    Rate().compute(pc_test, rate_pc)

    assert round(rate_pc.ram, 2) == 3.79

    assert round(rate_pc.data_storage, 2) == 4.02

    assert round(rate_pc.processor, 2) == 3.95

    assert round(rate_pc.rating, 2) == 4.61

    # Create a new Computer with components characteristics of pc with id = 1201
    pc_test = Desktop(chassis=ComputerChassis.Tower)
    data_storage = HardDrive(size=476940)
    data_storage.events_one.add(BenchmarkDataStorage(read_speed=158, write_speed=34.7))
    cpu = Processor(cores=2, speed=3.3)
    cpu.events_one.add(BenchmarkProcessor(rate=26339.48))
    pc_test.components |= {
        data_storage,
        RamModule(size=2048, speed=1333),
        cpu
    }
    # add functionality and appearance range
    rate_pc = WorkbenchRate(appearance_range=AppearanceRange.B,
                            functionality_range=FunctionalityRange.A)
    # Compute all components rates and general rating
    Rate().compute(pc_test, rate_pc)

    assert round(rate_pc.ram, 2) == 2.02

    assert round(rate_pc.data_storage, 2) == 4.07

    assert round(rate_pc.processor, 2) == 3.93

    assert round(rate_pc.rating, 2) == 3.48

    # Create a new Computer with components characteristics of pc with id = 79
    pc_test = Desktop(chassis=ComputerChassis.Tower)
    data_storage = HardDrive(size=76319)
    data_storage.events_one.add(BenchmarkDataStorage(read_speed=72.2, write_speed=24.3))
    cpu = Processor(cores=1, speed=1.6)
    cpu.events_one.add(BenchmarkProcessor(rate=3192.34))
    pc_test.components |= {
        data_storage,
        RamModule(size=512, speed=667),
        RamModule(size=512, speed=800),
        RamModule(size=512, speed=667),
        RamModule(size=512, speed=533),
        cpu
    }
    # add functionality and appearance range
    rate_pc = WorkbenchRate(appearance_range=AppearanceRange.C,
                            functionality_range=FunctionalityRange.A)
    # Compute all components rates and general rating
    Rate().compute(pc_test, rate_pc)

    assert round(rate_pc.ram, 2) == 1.99

    assert round(rate_pc.data_storage, 2) == 2.61

    assert round(rate_pc.processor, 2) == 1

    assert round(rate_pc.rating, 2) == 1.58

    # Create a new Computer with components characteristics of pc with id = 798
    pc_test = Desktop(chassis=ComputerChassis.Tower)
    data_storage = HardDrive(size=152587)
    data_storage.events_one.add(BenchmarkDataStorage(read_speed=78.1, write_speed=24.4))
    cpu = Processor(cores=2, speed=2.5)
    cpu.events_one.add(BenchmarkProcessor(rate=9974.3))
    pc_test.components |= {
        data_storage,
        RamModule(size=0, speed=None),
        cpu
    }
    # add functionality and appearance range
    rate_pc = WorkbenchRate(appearance_range=AppearanceRange.B,
                            functionality_range=FunctionalityRange.A)
    # Compute all components rates and general rating
    Rate().compute(pc_test, rate_pc)

    assert round(rate_pc.ram, 2) == 1

    assert round(rate_pc.data_storage, 2) == 3.7

    assert round(rate_pc.processor, 2) == 4.09

    assert round(rate_pc.rating, 2) == 2.5


@pytest.mark.xfail(reason='Data Storage rate actually requires a DSSBenchmark')
def test_rate_computer_with_data_storage_without_benchmark():
    """For example if the data storage was introduced manually
    or comes from an old version without benchmark."""
