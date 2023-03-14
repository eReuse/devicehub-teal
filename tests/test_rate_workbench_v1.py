"""This file test all corner cases when compute score v1.0.

First test to compute rate for every component in isolation.

Components in Score v1:
        -DataStorage
        -RamModule
        -Processor

Then some test compute rate with all components that use the algorithm

Excluded cases in tests

- No Processor
- No indispensable Benchmarks (Processor and Data Storage)
-

"""
import math

import pytest

from ereuse_devicehub.resources.action.models import (
    BenchmarkDataStorage,
    BenchmarkProcessor,
    VisualTest,
)
from ereuse_devicehub.resources.action.rate.v1_0 import (
    DataStorageRate,
    ProcessorRate,
    RamRate,
    RateAlgorithm,
)
from ereuse_devicehub.resources.device.models import (
    Desktop,
    HardDrive,
    Processor,
    RamModule,
)
from ereuse_devicehub.resources.enums import (
    AppearanceRange,
    ComputerChassis,
    FunctionalityRange,
)
from tests import conftest


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_data_storage_rate():
    """Test to check if compute data storage rate have same value than
    previous score version.
    """

    hdd_1969 = HardDrive(size=476940)
    hdd_1969.actions_one.add(BenchmarkDataStorage(read_speed=126, write_speed=29.8))

    data_storage_rate = DataStorageRate().compute([hdd_1969])

    assert math.isclose(data_storage_rate, 4.02, rel_tol=0.001)

    hdd_3054 = HardDrive(size=476940)
    hdd_3054.actions_one.add(BenchmarkDataStorage(read_speed=158, write_speed=34.7))

    # calculate DataStorage Rate
    data_storage_rate = DataStorageRate().compute([hdd_3054])

    assert math.isclose(data_storage_rate, 4.07, rel_tol=0.001)

    hdd_81 = HardDrive(size=76319)
    hdd_81.actions_one.add(BenchmarkDataStorage(read_speed=72.2, write_speed=24.3))

    data_storage_rate = DataStorageRate().compute([hdd_81])

    assert math.isclose(data_storage_rate, 2.61, rel_tol=0.001)

    hdd_1556 = HardDrive(size=152587)
    hdd_1556.actions_one.add(BenchmarkDataStorage(read_speed=78.1, write_speed=24.4))

    data_storage_rate = DataStorageRate().compute([hdd_1556])

    assert math.isclose(data_storage_rate, 3.70, rel_tol=0.001)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_data_storage_size_is_null():
    """Test where input DataStorage.size = NULL, BenchmarkDataStorage.read_speed = 0,
    BenchmarkDataStorage.write_speed = 0 is like no DataStorage has been detected;
    """

    hdd_null = HardDrive(size=None)
    hdd_null.actions_one.add(BenchmarkDataStorage(read_speed=0, write_speed=0))

    data_storage_rate = DataStorageRate().compute([hdd_null])
    assert data_storage_rate is None


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_no_data_storage():
    """Test without data storage devices."""

    hdd_null = HardDrive()
    hdd_null.actions_one.add(BenchmarkDataStorage(read_speed=0, write_speed=0))
    data_storage_rate = DataStorageRate().compute([hdd_null])
    assert data_storage_rate is None


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_ram_rate():
    """Test to check if compute ram rate have same value than previous
    score version only with 1 RamModule.
    """

    ram1 = RamModule(size=2048, speed=1333)

    ram_rate = RamRate().compute([ram1])

    assert math.isclose(
        ram_rate, 2.02, rel_tol=0.002
    ), 'RamRate returns incorrect value(rate)'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_ram_rate_2modules():
    """Test to check if compute ram rate have same value than previous
    score version with 2 RamModule.
    """

    ram1 = RamModule(size=4096, speed=1600)
    ram2 = RamModule(size=2048, speed=1067)

    ram_rate = RamRate().compute([ram1, ram2])

    assert math.isclose(
        ram_rate, 3.79, rel_tol=0.001
    ), 'RamRate returns incorrect value(rate)'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_ram_rate_4modules():
    """Test to check if compute ram rate have same value than previous
    score version with 2 RamModule.
    """

    ram1 = RamModule(size=512, speed=667)
    ram2 = RamModule(size=512, speed=800)
    ram3 = RamModule(size=512, speed=667)
    ram4 = RamModule(size=512, speed=533)

    ram_rate = RamRate().compute([ram1, ram2, ram3, ram4])

    assert math.isclose(
        ram_rate, 1.993, rel_tol=0.001
    ), 'RamRate returns incorrect value(rate)'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_ram_module_size_is_0():
    """Test where input data RamModule.size = 0; is like no RamModule
    has been detected.
    """

    ram0 = RamModule(size=0, speed=888)

    ram_rate = RamRate().compute([ram0])
    assert ram_rate is None


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_ram_speed_is_null():
    """Test where RamModule.speed is NULL (not detected) but has size."""

    ram0 = RamModule(size=2048, speed=None)

    ram_rate = RamRate().compute([ram0])

    assert math.isclose(
        ram_rate, 1.85, rel_tol=0.002
    ), 'RamRate returns incorrect value(rate)'

    ram0 = RamModule(size=1024, speed=None)

    ram_rate = RamRate().compute([ram0])

    assert math.isclose(
        ram_rate, 1.25, rel_tol=0.004
    ), 'RamRate returns incorrect value(rate)'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_no_ram_module():
    """Test without RamModule."""
    ram0 = RamModule()

    ram_rate = RamRate().compute([ram0])
    assert ram_rate is None


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_processor_rate():
    """Test to check if compute processor rate have same value than previous
    score version only with 1 core.
    """

    cpu = Processor(cores=1, speed=1.6)
    # add score processor benchmark
    cpu.actions_one.add(BenchmarkProcessor(rate=3192.34))

    processor_rate = ProcessorRate().compute(cpu)

    assert math.isclose(processor_rate, 1, rel_tol=0.001)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_processor_rate_2cores():
    """Test to check if compute processor rate have same value than previous
    score version with 2 cores.
    """

    cpu = Processor(cores=2, speed=3.4)
    # add score processor benchmark
    cpu.actions_one.add(BenchmarkProcessor(rate=27136.44))

    processor_rate = ProcessorRate().compute(cpu)

    assert math.isclose(processor_rate, 3.95, rel_tol=0.001)

    cpu = Processor(cores=2, speed=3.3)
    cpu.actions_one.add(BenchmarkProcessor(rate=26339.48))

    processor_rate = ProcessorRate().compute(cpu)

    assert math.isclose(processor_rate, 3.93, rel_tol=0.002)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_processor_with_null_cores():
    """Test with processor device have null number of cores."""
    cpu = Processor(cores=None, speed=3.3)
    cpu.actions_one.add(BenchmarkProcessor(rate=0))

    processor_rate = ProcessorRate().compute(cpu)

    assert math.isclose(processor_rate, 1.38, rel_tol=0.003)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_rate_processor_with_null_speed():
    """Test with processor device have null speed value."""
    cpu = Processor(cores=1, speed=None)
    cpu.actions_one.add(BenchmarkProcessor(rate=0))

    processor_rate = ProcessorRate().compute(cpu)

    assert math.isclose(processor_rate, 1.06, rel_tol=0.001)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_rate_computer_1193():
    """Test rate computer characteristics:
        - 2 module ram
        - processor with 2 cores

    Data get it from R score from DH pc with id = 1193

    pc_1193 = Computer()
    price = 92.2
    hdd_1969 = HardDrive(size=476940)
    hdd_1969.actions_one.add(BenchmarkDataStorage(read_speed=126, write_speed=29.8))
    ram1 = RamModule(size=4096, speed=1600)
    ram2 = RamModule(size=2048, speed=1067)
    cpu = Processor(cores=2, speed=3.4)
    cpu.actions_one.add(BenchmarkProcessor(rate=27136.44))
    pc_1193.components.add(hdd_1969, ram1, ram2, cpu)
    rate_pc_1193 = WorkbenchRate(appearance_range=AppearanceRange.A,
        functionality_range=FunctionalityRange.A)
    HDD_rate = 4.02
    RAM_rate = 3.79
    Processor_rate = 3.95
    Rating = 4.61
    """

    pc_test = Desktop(chassis=ComputerChassis.Tower)
    data_storage = HardDrive(size=476940)
    data_storage.actions_one.add(BenchmarkDataStorage(read_speed=126, write_speed=29.8))
    cpu = Processor(cores=2, speed=3.4)
    cpu.actions_one.add(BenchmarkProcessor(rate=27136.44))
    pc_test.components |= {
        data_storage,
        RamModule(size=4096, speed=1600),
        RamModule(size=2048, speed=1067),
        cpu,
    }
    # Add test visual with functionality and appearance range
    VisualTest(
        appearance_range=AppearanceRange.A,
        functionality_range=FunctionalityRange.A,
        device=pc_test,
    )

    # Compute all components rates and general rating
    rate_pc = RateAlgorithm().compute(pc_test)

    assert math.isclose(rate_pc.ram, 3.79, rel_tol=0.001)

    assert math.isclose(rate_pc.data_storage, 4.02, rel_tol=0.001)

    assert math.isclose(rate_pc.processor, 3.95, rel_tol=0.001)

    assert math.isclose(rate_pc.rating, 3.91, rel_tol=0.001)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_rate_computer_1201():
    """Test rate computer characteristics:
        - only 1 module ram
        - processor 2 cores

    Data get it from R score from DH pc with id = 1201

    pc_1201 = Computer()
    price = 69.6
    hdd_3054 = HardDrive(size=476940)
    hdd_3054.actions_one.add(BenchmarkDataStorage(read_speed=158, write_speed=34.7))
    ram1 = RamModule(size=2048, speed=1333)
    cpu = Processor(cores=2, speed=3.3)
    cpu.actions_one.add(BenchmarkProcessor(rate=26339.48))
    pc_1201.components.add(hdd_3054, ram1, cpu)
    rate_pc_1201 = WorkbenchRate(appearance_range=AppearanceRange.B,
        functionality_range=FunctionalityRange.A)
    HDD_rate = 4.07
    RAM_rate = 2.02
    Processor_rate = 3.93
    Rating = 3.48
    """

    pc_test = Desktop(chassis=ComputerChassis.Tower)
    data_storage = HardDrive(size=476940)
    data_storage.actions_one.add(BenchmarkDataStorage(read_speed=158, write_speed=34.7))
    cpu = Processor(cores=2, speed=3.3)
    cpu.actions_one.add(BenchmarkProcessor(rate=26339.48))
    pc_test.components |= {data_storage, RamModule(size=2048, speed=1333), cpu}
    # Add test visual with functionality and appearance range
    VisualTest(
        appearance_range=AppearanceRange.B,
        functionality_range=FunctionalityRange.A,
        device=pc_test,
    )

    # Compute all components rates and general rating
    rate_pc = RateAlgorithm().compute(pc_test)

    assert math.isclose(rate_pc.ram, 2.02, rel_tol=0.001)

    assert math.isclose(rate_pc.data_storage, 4.07, rel_tol=0.001)

    assert math.isclose(rate_pc.processor, 3.93, rel_tol=0.001)

    assert math.isclose(rate_pc.rating, 3.08, rel_tol=0.001)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_rate_computer_multiple_ram_module():
    """Test rate computer characteristics:
        - only 1 module ram
        - processor 2 cores

    Data get it from R score from DH pc with id = 79

    pc_79 = Computer()
    price = VeryLow
    hdd_81 = HardDrive(size=76319)
    hdd_81.actions_one.add(BenchmarkDataStorage(read_speed=72.2, write_speed=24.3))
    ram1 = RamModule(size=512, speed=667)
    ram2 = RamModule(size=512, speed=800)
    ram3 = RamModule(size=512, speed=667)
    ram4 = RamModule(size=512, speed=533)
    cpu = Processor(cores=1, speed=1.6)
    cpu.actions_one.add(BenchmarkProcessor(rate=3192.34))
    pc_79.components.add(hdd_81, ram1, ram2, ram3, ram4, cpu)
    # add functionality and appearance range
    rate_pc_79 = WorkbenchRate(appearance_range=AppearanceRange.C,
        functionality_range=FunctionalityRange.A)
    # add component rate
    HDD_rate = 2.61
    RAM_rate = 1.99
    Processor_rate = 1
    Rating = 1.58
    """

    pc_test = Desktop(chassis=ComputerChassis.Tower)
    data_storage = HardDrive(size=76319)
    data_storage.actions_one.add(
        BenchmarkDataStorage(read_speed=72.2, write_speed=24.3)
    )
    cpu = Processor(cores=1, speed=1.6)
    cpu.actions_one.add(BenchmarkProcessor(rate=3192.34))
    pc_test.components |= {
        data_storage,
        RamModule(size=512, speed=667),
        RamModule(size=512, speed=800),
        RamModule(size=512, speed=667),
        RamModule(size=512, speed=533),
        cpu,
    }
    # Add test visual with functionality and appearance range
    VisualTest(
        appearance_range=AppearanceRange.C,
        functionality_range=FunctionalityRange.A,
        device=pc_test,
    )
    # Compute all components rates and general rating
    rate_pc = RateAlgorithm().compute(pc_test)

    assert math.isclose(rate_pc.ram, 1.99, rel_tol=0.001)

    assert math.isclose(rate_pc.data_storage, 2.61, rel_tol=0.001)

    assert math.isclose(rate_pc.processor, 1, rel_tol=0.001)

    assert rate_pc.rating == 1.37


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_rate_computer_one_ram_module():
    """Test rate computer characteristics:
        - only 1 module ram
        - processor 2 cores

    Data get it from R score from DH pc with id = 798

    pc_798 = Computer()
    price = 50
    hdd_1556 = HardDrive(size=152587)
    hdd_1556.actions_one.add(BenchmarkDataStorage(read_speed=78.1, write_speed=24.4))
    ram0 = RamModule(size=0, speed=None)
    cpu = Processor(cores=2, speed=2.5)
    cpu.actions_one.add(BenchmarkProcessor(rate=9974.3))
    pc_798.components.add(hdd_1556, ram0, cpu)
    # add functionality and appearance range
    rate_pc_798 = WorkbenchRate(appearance_range=AppearanceRange.B,
        functionality_range=FunctionalityRange.A)
    # add component rate
    HDD_rate = 3.7
    RAM_rate = 1
    Processor_rate = 4.09
    Rating = 2.5
    """

    pc_test = Desktop(chassis=ComputerChassis.Tower)
    data_storage = HardDrive(size=152587)
    data_storage.actions_one.add(
        BenchmarkDataStorage(read_speed=78.1, write_speed=24.4)
    )
    cpu = Processor(cores=2, speed=2.5)
    cpu.actions_one.add(BenchmarkProcessor(rate=9974.3))
    pc_test.components |= {data_storage, RamModule(size=0, speed=None), cpu}
    # Add test visual with functionality and appearance range
    VisualTest(
        appearance_range=AppearanceRange.B,
        functionality_range=FunctionalityRange.A,
        device=pc_test,
    )

    # Compute all components rates and general rating
    rate_pc = RateAlgorithm().compute(pc_test)

    assert math.isclose(rate_pc.ram, 1, rel_tol=0.001)

    assert math.isclose(rate_pc.data_storage, 3.7, rel_tol=0.001)

    assert math.isclose(rate_pc.processor, 4.09, rel_tol=0.001)

    assert math.isclose(rate_pc.rating, 2.1, rel_tol=0.001)


@pytest.mark.xfail(reason='Data Storage rate actually requires a DSSBenchmark')
def test_rate_computer_with_data_storage_without_benchmark():
    """For example if the data storage was introduced manually
    or comes from an old version without benchmark.
    """
