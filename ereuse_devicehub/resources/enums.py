from distutils.version import StrictVersion
from enum import Enum, IntEnum, unique
from typing import Union


@unique
class SnapshotSoftware(Enum):
    """The algorithm_software used to perform the Snapshot."""
    Workbench = 'Workbench'
    AndroidApp = 'AndroidApp'
    Web = 'Web'
    DesktopApp = 'DesktopApp'


@unique
class RatingSoftware(Enum):
    """The algorithm_software used to compute the Score."""
    Ereuse = 'Ereuse'


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


@unique
class AggregateRatingVersions(Enum):
    v1 = StrictVersion('1.0')
    """
    This algorithm_version is set to aggregate :class:`ereuse_devicehub.resources.
    event.models.WorkbenchRate` algorithm_version X and :class:`ereuse_devicehub.
    resources.event.models.PhotoboxRate` algorithm_version Y.
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


@unique
class FunctionalityRange(Enum):
    """Grades the defects of a device that affect its usage."""
    # todo sync with https://github.com/ereuse/rdevicescore#input
    A = 'A. Everything works perfectly (buttons, and in case of screens there are no scratches)'
    B = 'B. There is a button difficult to press or a small scratch in an edge of a screen'
    C = 'C. A non-important button (or similar) doesn\'t work; screen has multiple scratches in edges'
    D = 'D. Multiple buttons don\'t work; screen has visual damage resulting in uncomfortable usage'


@unique
class Bios(Enum):
    """How difficult it has been to set the bios to boot from the network."""
    A = 'A. If by pressing a key you could access a boot menu with the network boot'
    B = 'B. You had to get into the BIOS, and in less than 5 steps you could set the network boot'
    C = 'C. Like B, but with more than 5 steps'
    D = 'D. Like B or C, but you had to unlock the BIOS (i.e. by removing the battery)'
    E = 'E. The device could not be booted through the network.'


@unique
class Orientation(Enum):
    Vertical = 'vertical'
    Horizontal = 'Horizontal'


@unique
class TestHardDriveLength(Enum):
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
    TestDataStorage = 'TestDataStorage'
    StressTest = 'StressTest'
    EraseSectors = 'EraseSectors'
    Install = 'Install'


BOX_RATE_5 = 1, 5
BOX_RATE_3 = 1, 3


# After looking at own databases

@unique
class RamInterface(Enum):
    DDR = 'DDR'
    DDR2 = 'DDR2'
    DDR3 = 'DDR3'
    DDR4 = 'DDR4'
    DDR5 = 'DDR5'
    DDR6 = 'DDR6'


@unique
class RamFormat(Enum):
    DIMM = 'DIMM'
    SODIMM = 'SODIMM'


@unique
class DataStorageInterface(Enum):
    ATA = 'ATA'
    USB = 'USB'
    PCI = 'PCI'


@unique
class ComputerMonitorTechnologies(Enum):
    CRT = 'Cathode ray tube (CRT)'
    TFT = 'Thin-film-transistor liquid-crystal (TFT)'
    LED = 'LED-backlit (LED)'
    PDP = 'Plasma display panel (Plasma)'
    LCD = 'Liquid-crystal display (any of TFT, LED, Blue Phase, IPS)'
    OLED = 'Organic light-emitting diode (OLED)'
    AMOLED = 'Organic light-emitting diode (AMOLED)'
