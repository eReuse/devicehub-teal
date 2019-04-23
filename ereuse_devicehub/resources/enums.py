from contextlib import suppress
from distutils.version import StrictVersion
from enum import Enum, IntEnum, unique
from typing import Set, Union

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


RATE_POSITIVE = 0, 10
RATE_NEGATIVE = -3, 5


@unique
class RatingRange(IntEnum):
    """
    The human translation to score range.

    You can compare them: ScoreRange.VERY_LOW < ScoreRange.LOW.
    There are four levels:

    1. Very low.
    2. Low.
    3. Medium.
    4. High.
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
    event.models.RateComputer` version X and :class:`ereuse_devicehub.
    resources.event.models.PhotoboxRate` version Y.
    """


@unique
class AppearanceRange(Enum):
    """
    This grade will be defined based on the aesthetics/cosmetic aspects, like visual damage or blemishes principally
    focused on chassis, physical buttons and screens.
    """
    Z = 'Z. The device is new'
    A = 'A. Is like new; without visual damage'
    B = 'B. Is in really good condition; small visual damage in difficult places to spot'
    C = 'C. Is in good condition; small visual damage in parts that are easy to spot, minor cosmetic blemishes on chassis)'
    D = 'D. Is acceptable; visual damage in visible parts, major cosmetic blemishes on chassis, missing cosmetic parts'
    E = 'E. Is unacceptable; severity visual damage, missing essential parts'
    NONE = 'NA. Grade doesn’t exists'


APPEARANCE_RANGE = 0.5, -0.3


@unique
class FunctionalityRange(Enum):
    """Based on usage condition of a device and its functionality aspects, like screen defect or camera defects"""
    A = 'A. All the buttons works perfectly, no screen/camera defects and chassis without usage issues'
    B = 'B. There is a button difficult to press or unstable it, a screen/camera defect or chassis problem'
    C = 'C.	Chassis defects or multiple buttons don\'t work; broken or unusable it, some screen/camera defect'
    D = 'D.	Chassis severity usage problems. All buttons, screen or camera don\'t work; broken or unusable it'
    NONE = 'NA. Grade doesn’t exists'



FUNCTIONALITY_RANGE = -0.3, 0.4


@unique
class BatteryHealthRange(Enum):
    """Grade the battery health status, depending on self report Android system"""
    A = 'A. The battery health is very good'
    B = 'B. Battery health is good'
    C = 'C.	Battery health is overheat / over voltage status but can stand the minimum duration'
    D = 'D.	Battery health is bad; can’t stand the minimum duration time'
    E = 'E. Battery health is very bad; and status is dead; unusable or miss it '
    NONE = 'NA. Grade doesn’t exists'



@unique
class BiosAccessRange(Enum):
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


class PrinterTechnology(Enum):
    """Technology of the printer."""
    Toner = 'Toner / Laser'
    Inkjet = 'Liquid inkjet'
    SolidInk = 'Solid ink'
    Dye = 'Dye-sublimation'
    Thermal = 'Thermal'


class Severity(IntEnum):
    """A flag evaluating the event execution. Ex. failed events
    have the value `Severity.Error`. Devicehub uses 4 severity levels:

    * Info: default neutral severity. The event succeeded.
    * Notice: The event succeeded but it is raising awareness.
      Notices are not usually that important but something
      (good or bad) worth checking.
    * Warning: The event succeeded but there is something important
      to check negatively affecting the event.
    * Error: the event failed.

    Devicehub specially raises user awareness when an event
    has a Severity of ``Warning`` or greater.
    """

    Info = 0
    Notice = 1
    Warning = 2
    Error = 3

    def __str__(self):
        if self == self.Info:
            m = '✓'
        elif self == self.Notice:
            m = 'ℹ️'
        elif self == self.Warning:
            m = '⚠'
        else:
            m = '❌'
        return m

    def __format__(self, format_spec):
        return str(self)


class PhysicalErasureMethod(Enum):
    """Methods of physically erasing the data-storage, usually
    destroying the whole component.

    Certified data-storage destruction mean, as of `UNE-EN 15713
    <https://www.une.org/encuentra-tu-norma/busca-tu-norma/norma?c=N0044792>`_,
    reducing the material to a size making it undecipherable, illegible,
    and non able to be re-built.
    """

    Shred = 'Reduction of the data-storage to the required certified ' \
            'standard sizes.'
    Disintegration = 'Reduction of the data-storage to smaller sizes ' \
                     'than the certified standard ones.'

    def __str__(self):
        return self.name


class ErasureStandards(Enum):
    """Software erasure standards."""

    HMG_IS5 = 'British HMG Infosec Standard 5 (HMG IS5)'
    """`British HMG Infosec Standard 5 (HMG IS5) 
    <https://en.wikipedia.org/wiki/Infosec_Standard_5>`_.
    
    In order to follow this standard, an erasure must have the
    following steps:
    
    1. A first step writing zeroes to the data-storage units.
    2. A second step erasing with random data, verifying the erasure
       success in each hard-drive sector.
    
    And be an :class:`ereuse_devicehub.resources.event.models.EraseSectors`.
    """

    def __str__(self):
        return self.value

    @classmethod
    def from_data_storage(cls, erasure) -> Set['ErasureStandards']:
        """Returns a set of erasure standards."""
        from ereuse_devicehub.resources.event import models as events
        standards = set()
        if isinstance(erasure, events.EraseSectors):
            with suppress(ValueError):
                first_step, *other_steps = erasure.steps
                if isinstance(first_step, events.StepZero) \
                        and all(isinstance(step, events.StepRandom) for step in other_steps):
                    standards.add(cls.HMG_IS5)
        return standards
