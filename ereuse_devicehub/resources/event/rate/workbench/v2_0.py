from enum import Enum
from typing import Iterable

from ereuse_devicehub.resources.device.models import DataStorage, Processor, RamModule, Device
from ereuse_devicehub.resources.event.models import BenchmarkDataStorage, WorkbenchRate
from ereuse_devicehub.resources.event.rate.rate import BaseRate


class Rate(BaseRate):
    """
     Rate all the categories of a device
     RATE = Quality Rate + Functionality Rate + Appearance Rate
     """

    class Range(Enum):
        @classmethod
        def from_devicehub(cls, r: Enum):
            return getattr(cls, r.name) if r else cls.NONE

    def compute(self, device: Device):
        rate_quality = QualityRate.compute()
        rate_functionality = FunctionalityRate.compute()
        rate_appearance = self.Appearance.from_devicehub(rate.appearance_range).value

        # Final result
        return round(max(rate_quality + rate_functionality + rate_appearance, 0), 2)


class QualityRate(BaseRate):
    """
    Rate Quality aspect
    Display (screen)
    Processor
    RAM
    Data Storage
    Battery
    Camera
    """
    """
    List components wieghts
    total_weights = 1
    """
    DISPLAY_WEIGHT = 0.25
    PROCESSOR_WEIGHT = 0.1
    RAM_WEIGHT = 0.25
    DATA_STORAGE_WEIGHT = 0.05
    BATTERY_WEIGHT = 0.25
    CAMERA_WEIGHT = 0.1

    def __init__(self) -> None:
        super().__init__()
        # TODO Check if component exists before rate it.
        self.RATES = {
            # composition: type: (field, compute class)
            Display.t: ('display', DisplayRate()),
            Processor.t: ('processor', ProcessorRate()),
            RamModule.t: ('ram', RamRate()),
            DataStorage.t: ('data_storage', DataStorageRate()),
            Battery.t: ('battery', BatteryRate()),
            Camera.t: ('camera', CameraRate())
        }

    def compute(self, device: Device):
        rate = self.RATES
        # TODO Assign only the weight of existing components.
        weights = (
            self.DISPLAY_WEIGHT, self.PROCESSOR_WEIGHT, self.RAM_WEIGHT, self.DATA_STORAGE_WEIGHT, self.BATTERY_WEIGHT,
            self.CAMERA_WEIGHT)

        return self.harmonic_mean(weights, rate)


class FunctionalityRate(BaseRate):
    """
    Rate Functionality aspects on mobile devices

    """

    # Functionality Range v2
    A = 0, 5
    B = 0
    C = -0, 25
    D = -0, 5
    NONE = -0, 3

    # SUM(weights) = 1
    SIM_WEIGHT = 0.2
    USB_WEIGHT = 0.25
    WIFI_WEIGHT = 0.05
    BLUETOOTH_WEIGHT = 0.05
    FINGERPRINT_WEIGHT = 0.05
    LOUDSPEAKER_WEIGHT = 0.15
    MICROPHONE_WEIGHT = 0.15

    def compute(self, FunctionalityRate: FunctionalityRate):
        """

        :param FunctionalityDevice: List[Boolean]
        :return:
        """
        # TODO Check if funcionality aspect is != NULL
        sim = FunctionalityDevice.sim * self.SIM_WEIGHT
        usb = FunctionalityDevice.usb * self.USB_WEIGHT
        wifi = FunctionalityDevice.wifi * self.WIFI_WEIGHT
        bt = FunctionalityDevice.bt * self.BLUETOOTH_WEIGHT
        fingerprint = FunctionalityDevice.fingerprint * self.FINGERPRINT_WEIGHT
        loudspeaker = FunctionalityDevice.loudspeaker * self.LOUDSPEAKER_WEIGHT
        microphone = FunctionalityDevice.microphone * self.MICROPHONE_WEIGHT

        functionality_rate = (sim + usb + wifi + bt + fingerprint + loudspeaker + microphone)
        # TODO Add functionality range (buttons, chassis, display defects, camera defects)
        return functionality_rate


class Appearance(Range):
    """
    APPEARANCE GRADE  [0.5,-0.5]
    Enum(AppearanceRangev2)
    """

    Z = 0.5
    A = 0.4
    B = 0.1
    C = -0.1
    D = -0.25
    E = -0.5
    NONE = -0.3


class FinalRate(Rate):
    """The act of grading the appearance, quality (performance), and functionality
        of a device.

        There are five categories of ``Rate``:
        1. ``Quality``. How good is the machine, in terms of performance.
        2. ``Functionality``.
        3. ``Appearance``.
        4. ``Market value``.
        5. ``Cost of repair``.

        There are types of rating a device:

        1. Rate Quality
        2. Rate Functionality
        3. Rate Final
        """
    quality_rate = QualityRate()
    functionality_rate = FunctionalityRate()
    appearance_rate = Appearance()

    final_rate = None

    # TODO Develop merge rate aspects (categories)

    """     MANUAL INPUT      """
    manual_id = Column(UUID(as_uuid=True), ForeignKey(ManualRate.id))
    manual_id.comment = """The ManualEvent used to generate this
      aggregation, or None if none used.

      An example of ManualEvent is using the web or the Android app
      to rate a device.
      """
    manual = relationship(ManualRate,
                          backref=backref('aggregate_rate_manual',
                                          lazy=True,
                                          order_by=lambda: ResultRate.created,
                                          collection_class=OrderedSet),
                          primaryjoin=manual_id == ManualRate.id)

    """     WORKBENCH COMPUTER       """
    workbench_computer_id = Column(UUID(as_uuid=True), ForeignKey(QualityRateComputer.id))
    workbench_computer_id.comment = """The WorkbenchRate used to generate
    this aggregation, or None if none used.
    """
    workbench_computer = relationship(QualityRateComputer,
                                      backref=backref('aggregate_rate_workbench',
                                                      lazy=True,
                                                      order_by=lambda: ResultRate.created,
                                                      collection_class=OrderedSet),
                                      primaryjoin=workbench_computer_id == QualityRateComputer.id)

    """     WORKBENCH MOBILE       """

    workbench_mobile_id = Column(UUID(as_uuid=True), ForeignKey(QualityRateMobile.id))
    workbench_mobile_id.comment = """The WorkbenchRate used to generate
    this aggregation, or None if none used.
    """
    workbench_mobile = relationship(QualityRateMobile,
                                    backref=backref('aggregate_rate_workbench',
                                                    lazy=True,
                                                    order_by=lambda: ResultRate.created,
                                                    collection_class=OrderedSet),
                                    primaryjoin=workbench_mobile_id == QualityRateMobile.id)

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault('version', StrictVersion('1.0'))
        super().__init__(*args, **kwargs)

    @classmethod
    def quality_rate(cls, quality: QualityRate):
        pass

    @classmethod
    def functionality_rate(cls, func: FunctionalityRate):
        pass

    @classmethod
    def final_rate(cls, rate: Rate):
        pass

    # Categories

    @classmethod
    def quality_category(cls, quality: QualityRate):
        pass

    @classmethod
    def functionality_category(cls, quality: QualityRate):
        pass

    @classmethod
    def appearance_category(cls, quality: QualityRate):
        pass

    @classmethod
    def maket_value_category(cls, quality: QualityRate):
        pass

    @classmethod
    def cost_of_repair_category(cls, quality: QualityRate):
        pass


class DisplayRate(QualityRate):
    """
     Calculate a DisplayRate
     """
    SIZE_NORM = 3.5, 7.24
    RESOLUTION_H_NORM = 440, 1080
    RESOLUTION_W_NORM = 720, 2048

    DISPLAY_WEIGHTS = 0.6, 0.2, 0.2

    def compute(self, display: Display):
        size = display.size or self.DEFAULT_SIZE
        resolution_h = display.resolution_h or 0
        resolution_w = display.resolution_w or 0

        # STEP: Normalize values
        size_norm = max(self.norm(size, *self.SIZE_NORM), 0)
        resolution_h_norm = max(self.norm(resolution_h, *self.RESOLUTION_H_NORM), 0)
        resolution_w_norm = max(self.norm(resolution_w, *self.RESOLUTION_W_NORM), 0)

        # STEP: Fusion Characteristics
        return self.harmonic_mean(self.DISPLAY_WEIGHTS, rates=(size_norm, resolution_h_norm, resolution_w_norm))


# COMPONENTS RATE V1 (PROCESSOR,RAM,HHD)

# TODO quality components rate qualityrate class??

class ProcessorRate(QualityRate):
    """
    Calculate a ProcessorRate
    """
    # processor.xMin, processor.xMax
    PROCESSOR_NORM = 3196.17, 17503.81
    CORES_NORM = 1, 6

    DEFAULT_CORES = 1
    DEFAULT_SPEED = 1.6
    DEFAULT_SCORE = 4000

    PROCESSOR_WEIGHTS = 0.5, 0.5

    def compute(self, processor: Processor):
        """ Compute processor rate
            Obs: cores and speed are possible NULL value
            :return: result is a rate (score) of Processor characteristics
        """
        cores = processor.cores or self.DEFAULT_CORES
        speed = processor.speed or self.DEFAULT_SPEED

        # STEP: Normalize values
        cores_norm = max(self.norm(cores, *self.PROCESSOR_NORM), 0)
        cpu_speed_norm = max(self.norm(speed, *self.CORES_NORM), 0)

        # STEP: Fusion Characteristics
        return self.harmonic_mean(self.PROCESSOR_WEIGHTS, rates=(cores_norm, cpu_speed_norm))


class RamRate(QualityRate):
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

    def compute(self, ram_devices: Iterable[RamModule]):
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

            _speed = ram.speed or 0
            speed += _speed

        # STEP: Normalize values
        size_norm = max(self.norm(size, *self.SIZE_NORM), 0)
        ram_speed_norm = max(self.norm(speed, *self.RAM_SPEED_NORM), 0)

        # STEP: Fusion Characteristics
        return self.harmonic_mean(self.RAM_WEIGHTS, rates=(size_norm, ram_speed_norm))


class DataStorageRate(QualityRate):
    """
    Calculate the rate of all DataStorage devices
    """
    # drive.size.xMin; drive.size.xMax
    SIZE_NORM = 4096, 265000
    READ_SPEED_NORM = 2.7, 109.5
    WRITE_SPEED_NORM = 2, 27.35
    # drive.size.weight; drive.readingSpeed.weight; drive.writingSpeed.weight;
    DATA_STORAGE_WEIGHTS = 0.5, 0.25, 0.25

    def compute(self, data_storage_devices: Iterable[DataStorage], rate: WorkbenchRate):
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

            # STEP: Fusion Characteristics
            return self.harmonic_mean(self.DATA_STORAGE_WEIGHTS,
                                      rates=(size_norm, read_speed_norm, write_speed_norm))


class BatteryRate(QualityRate):
    """
    Rate Battery component if device Type = {Mobile Devices}
    """
    CAPACITY_NORM = 2200, 6000
    DEFAULT_CAPACITY = 3000

    def compute(self, display: Display):
        capacity = battery.capacity or self.DEFAULT_CAPACITY

        # STEP: Normalize values
        capacity_norm = max(self.norm(capacity, *self.CAPACITY_NORM), 0)

        return capacity_norm


class CameraRate(QualityRate):
    """
    Rate camera component if exist on device
    """
    RESOLUTION_NORM = 2200, 6000
    DEFAULT_RESOLUTION = 16

    def compute(self, display: Display):
        resolution = camera.resolution or self.DEFAULT_RESOLUTION

        # STEP: Normalize values
        resolution_norm = max(self.norm(resolution, *self.RESOLUTION_NORM), 0)

        return resolution_norm
