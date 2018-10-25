from distutils.version import StrictVersion
from enum import Enum, IntEnum, unique
from typing import Union

import inflection


@unique
class SnapshotSoftware(Enum):
    """The software used to perform the Snapshot."""
    Workbench = 'Workbench'
    AndroidApp = 'AndroidApp'
    Web = 'Web'
    DesktopApp = 'DesktopApp'

    def __str__(self):
        return self.name


@unique
class RatingSoftware(Enum):
    """The software used to compute the Score."""
    ECost = 'ECost'
    """
    The eReuse.org rate algorithm that focuses maximizing refurbishment
    of devices in general, specially penalizing very low and very high
    devices in order to stimulate medium-range devices.
    
    This model is cost-oriented. 
    """
    EMarket = 'EMarket'

    def __str__(self):
        return self.name


RATE_POSITIVE = 0, 10
RATE_NEGATIVE = -3, 5


@unique
class RatingRange(IntEnum):
    """
    The human translation to score range.

    You can compare them: ScoreRange.VERY_LOW < ScoreRange.LOW
    """
    VERY_LOW = 2
    LOW = 3
    MEDIUM = 4
    HIGH = 5

    @classmethod
    def from_score(cls, val: Union[int, float]) -> 'RatingRange':
        assert 0 <= val <= 10, 'Value is not a valid score.'

        if val <= cls.VERY_LOW:
            return cls.VERY_LOW
        elif val <= cls.LOW:
            return cls.LOW
        elif val <= cls.MEDIUM:
            return cls.MEDIUM
        else:
            return cls.HIGH

    def __str__(self):
        return inflection.humanize(self.name)

    def __format__(self, format_spec):
        return str(self)


@unique
class PriceSoftware(Enum):
    Ereuse = 'Ereuse'


@unique
class AggregateRatingVersions(Enum):
    v1 = StrictVersion('1.0')
    """
    This version is set to aggregate :class:`ereuse_devicehub.resources.
    event.models.WorkbenchRate` version X and :class:`ereuse_devicehub.
    resources.event.models.PhotoboxRate` version Y.
    """


@unique
class AppearanceRange(Enum):
    """Grades the imperfections that aesthetically affect the device, but not its usage."""
    Z = '0. The device is new.'
    A = 'A. Is like new (without visual damage)'
    B = 'B. Is in really good condition (small visual damage in difficult places to spot)'
    C = 'C. Is in good condition (small visual damage in parts that are easy to spot, not screens)'
    D = 'D. Is acceptable (visual damage in visible parts, not screens)'
    E = 'E. Is unacceptable (considerable visual damage that can affect usage)'

    def __str__(self):
        return self.name


@unique
class FunctionalityRange(Enum):
    """Grades the defects of a device that affect its usage."""
    # todo sync with https://github.com/ereuse/rdevicescore#input
    A = 'A. Everything works perfectly (buttons, and in case of screens there are no scratches)'
    B = 'B. There is a button difficult to press or a small scratch in an edge of a screen'
    C = 'C. A non-important button (or similar) doesn\'t work; screen has multiple scratches in edges'
    D = 'D. Multiple buttons don\'t work; screen has visual damage resulting in uncomfortable usage'

    def __str__(self):
        return self.name


@unique
class Bios(Enum):
    """How difficult it has been to set the bios to boot from the network."""
    A = 'A. If by pressing a key you could access a boot menu with the network boot'
    B = 'B. You had to get into the BIOS, and in less than 5 steps you could set the network boot'
    C = 'C. Like B, but with more than 5 steps'
    D = 'D. Like B or C, but you had to unlock the BIOS (i.e. by removing the battery)'
    E = 'E. The device could not be booted through the network.'

    def __str__(self):
        return self.name


@unique
class Orientation(Enum):
    Vertical = 'vertical'
    Horizontal = 'Horizontal'


@unique
class TestDataStorageLength(Enum):
    Short = 'Short'
    Extended = 'Extended'


@unique
class ImageSoftware(Enum):
    Photobox = 'Photobox'


@unique
class ImageMimeTypes(Enum):
    """Supported image Mimetypes for Devicehub."""
    jpg = 'image/jpeg'
    png = 'image/png'


@unique
class SnapshotExpectedEvents(Enum):
    """Events that Workbench can perform when processing a device."""
    Benchmark = 'Benchmark'
    TestDataStorage = 'TestDataStorage'
    StressTest = 'StressTest'
    EraseBasic = 'EraseBasic'
    EraseSectors = 'EraseSectors'
    SmartTest = 'SmartTest'
    Install = 'Install'


BOX_RATE_5 = 1, 5
BOX_RATE_3 = 1, 3


# After looking at own databases

@unique
class RamInterface(Enum):
    """
    The interface or type of RAM.

    The more common type of RAM nowadays for RamModules is SDRAM.
    Note that we have not added all sub-types (please contact if
    you want them). See more here
    https://en.wikipedia.org/wiki/Category:SDRAM.

    Although SDRAM is the generic naming for any DDR we include it
    here for those cases where there is no more specific information.
    Please, try to always use DDRø-6 denominations.
    """
    SDRAM = 'SDRAM'
    DDR = 'DDR SDRAM'
    DDR2 = 'DDR2 SDRAM'
    DDR3 = 'DDR3 SDRAM'
    DDR4 = 'DDR4 SDRAM'
    DDR5 = 'DDR5 SDRAM'
    DDR6 = 'DDR6 SDRAM'

    def __str__(self):
        return self.value


@unique
class RamFormat(Enum):
    DIMM = 'DIMM'
    SODIMM = 'SODIMM'

    def __str__(self):
        return self.value


@unique
class DataStorageInterface(Enum):
    ATA = 'ATA'
    USB = 'USB'
    PCI = 'PCI'

    def __str__(self):
        return self.value


@unique
class DisplayTech(Enum):
    CRT = 'Cathode ray tube (CRT)'
    TFT = 'Thin-film-transistor liquid-crystal (TFT)'
    LED = 'LED-backlit (LED)'
    PDP = 'Plasma display panel (Plasma)'
    LCD = 'Liquid-crystal display (any of TFT, LED, Blue Phase, IPS)'
    OLED = 'Organic light-emitting diode (OLED)'
    AMOLED = 'Organic light-emitting diode (AMOLED)'

    def __str__(self):
        return self.name


@unique
class ComputerChassis(Enum):
    """The chassis of a computer."""
    Tower = 'Tower'
    Docking = 'Docking'
    AllInOne = 'All in one'
    Microtower = 'Microtower'
    PizzaBox = 'Pizza box'
    Lunchbox = 'Lunchbox'
    Stick = 'Stick'
    Netbook = 'Netbook'
    Handheld = 'Handheld'
    Laptop = 'Laptop'
    Convertible = 'Convertible'
    Detachable = 'Detachable'
    Tablet = 'Tablet'
    Virtual = 'Non-physical device'

    def __str__(self):
        return inflection.humanize(inflection.underscore(self.value))


class ReceiverRole(Enum):
    """
    The role that the receiver takes in the reception;
    the meaning of the reception.
    """
    Intermediary = 'Generic user in the workflow of the device.'
    FinalUser = 'The user that will use the device.'
    CollectionPoint = 'A collection point.'
    RecyclingPoint = 'A recycling point.'
    Transporter = 'An user that ships the devices to another one.'


class DataStoragePrivacyCompliance(Enum):
    EraseBasic = 'EraseBasic'
    EraseBasicError = 'EraseBasicError'
    EraseSectors = 'EraseSectors'
    EraseSectorsError = 'EraseSectorsError'
    Destruction = 'Destruction'
    DestructionError = 'DestructionError'

    @classmethod
    def from_erase(cls, erasure) -> 'DataStoragePrivacyCompliance':
        """Returns the correct enum depending of the passed-in erasure."""
        from ereuse_devicehub.resources.event.models import EraseSectors
        if isinstance(erasure, EraseSectors):
            return cls.EraseSectors if not erasure.error else cls.EraseSectorsError
        else:
            return cls.EraseBasic if not erasure.error else cls.EraseBasicError


class PrinterTechnology(Enum):
    """Technology of the printer."""
    Toner = 'Toner / Laser'
    Inkjet = 'Liquid inkjet'
    SolidInk = 'Solid ink'
    Dye = 'Dye-sublimation'
    Thermal = 'Thermal'
