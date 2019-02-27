import math

from ereuse_devicehub.resources.device.models import HardDrive, Processor, RamModule, Device
from ereuse_devicehub.resources.event.rate.workbench.v2_0 import Rate


def test_ratev2_general():
    """
    Test to check if compute all aspects (quality, functionality and appearance) correctly

    Quality rate aspects:
        Display (screen)
        Processor
        RAM
        Data Storage
        Battery
        Camera

    Functionality rate aspects on mobile devices
        SIM
        USB/ Charger plug
        Wi-Fi
        Bluetooth
        Fingerprint sensor
        Loudspeaker
        Microphone


    """
    device_test = Device()
    device_test.components |= {
        Processor(cores=2, speed=3.4),  # CPU
        HardDrive(size=476940),  # HDD
        RamModule(size=4096, speed=1600),  # RAM
        RamModule(size=2048, speed=1067),  # RAM
        Display(size=5.5, resolutionH=1080, resolutionW=1920),  # Screen
        Battery(capacity=3000),  # Mobile devices
        Camera(resolution=16)
    }

    rate_device = Rate().compute(device_test)

    assert math.isclose(rate_device, 2.2, rel_tol=0.001)


def test_quality_rate():
    """ Test to check all quality aspects
    """
    pass


def test_functionality_rate():
    """
    Test to check all functionality aspects
    :return:
    """
    pass


def test_component_rate_equal_to_zero():
    """
    Test to check all functionality aspects
    :return:
    """
    pass


def tes_component_rate_is_null():
    """
    Test to check all functionality aspects
    :return:
    """
    pass
