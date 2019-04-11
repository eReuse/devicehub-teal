from enum import Enum
from itertools import groupby
from typing import Iterable

from ereuse_devicehub.resources.device.models import Computer, DataStorage, Desktop, Laptop, \
    Processor, RamModule, Server
from ereuse_devicehub.resources.event.models import BenchmarkDataStorage, BenchmarkProcessor, \
    RateComputer, TestVisual
# todo if no return assign then rate_c = 1 is assigned
# todo fix corner cases, like components characteristics == None
from ereuse_devicehub.resources.event.rate.rate import BaseRate


class RateAlgorithm(BaseRate):
    """
    Rate all components in Computer
    """

    class Range(Enum):
        @classmethod
        def from_devicehub(cls, r: Enum):
            return getattr(cls, r.name) if r else cls.NONE

    class Appearance(Range):
        Z = 0.5
        A = 0.3
        B = 0
        C = -0.2
        D = -0.5
        E = -1.0
        NONE = -0.3

    class Functionality(Range):
        A = 0.4
        B = -0.5
        C = -0.75
        D = -1
        NONE = -0.3

    def __init__(self) -> None:
        super().__init__()
        self.RATES = {
            # composition: type: (field, compute class)
            Processor.t: ('processor', ProcessorRate()),
            RamModule.t: ('ram', RamRate()),
            DataStorage.t: ('data_storage', DataStorageRate())
        }

    def compute(self, device: Computer):
        """
        Compute RateComputer is a rate (score) ranging from 0 to 4.7
        that represents estimating value of use of desktop and laptop computer components.

        This mutates "rate".
        """
        assert isinstance(device, (Desktop, Laptop, Server))

        rate = RateComputer()

        rate.processor = rate.data_storage = rate.ram = 1  # Init

        # Group cpus, rams, storages and compute their rate
        # Treat the same way with HardDrive and SolidStateDrive like (DataStorage)
        clause = lambda x: DataStorage.t if isinstance(x, DataStorage) else x.t
        c = (c for c in device.components if clause(c) in set(self.RATES.keys()))
        for type, components in groupby(sorted(c, key=clause), key=clause):
            if type == Processor.t:  # ProcessorRate.compute expects only 1 processor
                components = next(components)
            field, rate_cls = self.RATES[type]  # type: str, BaseRate
            result = rate_cls.compute(components, rate)
            if result:
                setattr(rate, field, result)

        rate_components = self.harmonic_mean_rates(rate.processor, rate.data_storage, rate.ram)
        rate.appearance = self.Appearance.from_devicehub(TestVisual.appearance_range).value
        rate.functionality = self.Functionality.from_devicehub(TestVisual.functionality_range).value

        rate.rating = round(max(rate_components + rate.functionality + rate.appearance, 0), 2)
        rate.appearance = round(rate.appearance, 2)
        rate.functionality = round(rate.functionality, 2)
        rate.processor = round(rate.processor, 2)
        rate.ram = round(rate.ram, 2)
        rate.data_storage = round(rate.data_storage, 2)
        device.events_one.add(rate)
        return rate


class ProcessorRate(BaseRate):
    """
    Calculate a ProcessorRate of all Processor devices
    """
    # processor.xMin, processor.xMax
    PROCESSOR_NORM = 3196.17, 17503.81

    DEFAULT_CORES = 1
    DEFAULT_SPEED = 1.6
    # In case of i2, i3,.. result penalized.
    # Intel(R) Core(TM) i3 CPU 530 @ 2.93GHz, score = 23406.92 but results inan score of 17503.
    DEFAULT_SCORE = 4000

    def compute(self, processor: Processor, rate: RateComputer):
        """ Compute processor rate
            Obs: cores and speed are possible NULL value
            :return: result is a rate (score) of Processor characteristics
        """
        # todo for processor_device in processors; more than one processor
        cores = processor.cores or self.DEFAULT_CORES
        speed = processor.speed or self.DEFAULT_SPEED
        # todo fix StopIteration if don't exists BenchmarkProcessor
        benchmark_cpu = next(e for e in processor.events if isinstance(e, BenchmarkProcessor))
        # todo fix if benchmark_cpu.rate == 0
        benchmark_cpu = benchmark_cpu.rate or self.DEFAULT_SCORE

        # STEP: Fusion components
        processor_rate = (benchmark_cpu + speed * 2000 * cores) / 2  # todo magic number!

        # STEP: Normalize values
        processor_norm = max(self.norm(processor_rate, *self.PROCESSOR_NORM), 0)

        # STEP: Compute rate/score from every component
        # Calculate processor_rate
        if processor_norm >= self.CEXP:
            processor_rate = self.rate_exp(processor_norm)
        if self.CLIN <= processor_norm < self.CLOG:
            processor_rate = self.rate_lin(processor_norm)
        if processor_norm >= self.CLOG:
            processor_rate = self.rate_log(processor_norm)

        assert processor_rate, 'Could not rate processor.'
        return processor_rate


class RamRate(BaseRate):
    """
    Calculate a RamRate of all RamModule devices
    """
    # ram.size.xMin; ram.size.xMax
    SIZE_NORM = 256, 8192
    RAM_SPEED_NORM = 133, 1333
    # ram.speed.factor
    RAM_SPEED_FACTOR = 3.7
    # ram.size.weight; ram.speed.weight;
    RAM_WEIGHTS = 0.7, 0.3

    def compute(self, ram_devices: Iterable[RamModule], rate: RateComputer):
        """
        Obs: RamModule.speed is possible NULL value & size != NULL or NOT??
        :return: result is a rate (score) of all RamModule components
        """
        size = 0.0
        speed = 0.0

        # STEP: Filtering, data cleaning and merging of component parts
        for ram in ram_devices:
            _size = ram.size or 0
            size += _size
            if ram.speed:
                speed += (ram.speed or 0) * _size
            else:
                speed += (_size / self.RAM_SPEED_FACTOR) * _size

        # STEP: Fusion components
        # To guarantee that there will be no 0/0
        if size:
            speed /= size

            # STEP: Normalize values
            size_norm = max(self.norm(size, *self.SIZE_NORM), 0)
            ram_speed_norm = max(self.norm(speed, *self.RAM_SPEED_NORM), 0)

            # STEP: Compute rate/score from every component
            # Calculate size_rate
            if self.CEXP <= size_norm < self.CLIN:
                size_rate = self.rate_exp(size_norm)
            if self.CLIN <= size_norm < self.CLOG:
                size_rate = self.rate_lin(size_norm)
            if size_norm >= self.CLOG:
                size_rate = self.rate_log(size_norm)
            # Calculate ram_speed_rate
            if self.CEXP <= ram_speed_norm < self.CLIN:
                ram_speed_rate = self.rate_exp(ram_speed_norm)
            if self.CLIN <= ram_speed_norm < self.CLOG:
                ram_speed_rate = self.rate_lin(ram_speed_norm)
            if ram_speed_norm >= self.CLOG:
                ram_speed_rate = self.rate_log(ram_speed_norm)

            # STEP: Fusion Characteristics
            return self.harmonic_mean(self.RAM_WEIGHTS, rates=(size_rate, ram_speed_rate))


class DataStorageRate(BaseRate):
    """
    Calculate the rate of all DataStorage devices
    """
    # drive.size.xMin; drive.size.xMax
    SIZE_NORM = 4, 265000
    READ_SPEED_NORM = 2.7, 109.5
    WRITE_SPEED_NORM = 2, 27.35
    # drive.size.weight; drive.readingSpeed.weight; drive.writingSpeed.weight;
    DATA_STORAGE_WEIGHTS = 0.5, 0.25, 0.25

    def compute(self, data_storage_devices: Iterable[DataStorage], rate: RateComputer):
        """
        Obs: size != NULL and 0 value & read_speed and write_speed != NULL
        :return: result is a rate (score) of all DataStorage devices
        """
        size = 0
        read_speed = 0
        write_speed = 0

        # STEP: Filtering, data cleaning and merging of component parts
        for storage in data_storage_devices:
            # todo fix StopIteration if don't exists BenchmarkDataStorage
            benchmark = next(e for e in storage.events if isinstance(e, BenchmarkDataStorage))
            # prevent NULL values
            _size = storage.size or 0
            size += _size
            read_speed += benchmark.read_speed * _size
            write_speed += benchmark.write_speed * _size

        # STEP: Fusion components
        # Check almost one storage have size, try catch exception 0/0
        if size:
            read_speed /= size
            write_speed /= size

            # STEP: Normalize values
            size_norm = max(self.norm(size, *self.SIZE_NORM), 0)
            read_speed_norm = max(self.norm(read_speed, *self.READ_SPEED_NORM), 0)
            write_speed_norm = max(self.norm(write_speed, *self.WRITE_SPEED_NORM), 0)

            # STEP: Compute rate/score from every component
            # Calculate size_rate
            if size_norm >= self.CLOG:
                size_rate = self.rate_log(size_norm)
            elif self.CLIN <= size_norm < self.CLOG:
                size_rate = self.rate_lin(size_norm)
            elif self.CEXP <= size_norm < self.CLIN:
                size_rate = self.rate_exp(size_norm)
            # Calculate read_speed_rate
            if read_speed_norm >= self.CLOG:
                read_speed_rate = self.rate_log(read_speed_norm)
            elif self.CLIN <= read_speed_norm < self.CLOG:
                read_speed_rate = self.rate_lin(read_speed_norm)
            elif self.CEXP <= read_speed_norm < self.CLIN:
                read_speed_rate = self.rate_exp(read_speed_norm)
            # write_speed_rate
            if write_speed_norm >= self.CLOG:
                write_speed_rate = self.rate_log(write_speed_norm)
            elif self.CLIN <= write_speed_norm < self.CLOG:
                write_speed_rate = self.rate_lin(write_speed_norm)
            elif self.CEXP <= write_speed_norm < self.CLIN:
                write_speed_rate = self.rate_exp(write_speed_norm)

            # STEP: Fusion Characteristics
            return self.harmonic_mean(self.DATA_STORAGE_WEIGHTS,
                                      rates=(size_rate, read_speed_rate, write_speed_rate))


rate_algorithm = RateAlgorithm()
