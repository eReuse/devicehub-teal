import math

import pytest

from ereuse_devicehub.resources.device.models import HardDrive, Processor, RamModule, Device
from ereuse_devicehub.resources.event.rate.workbench.v2_0 import Rate


@pytest.mark.xfail(reason='Evaluate')
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


@pytest.mark.xfail(reason='Develop')
def test_general_rate_without_quality():
    """
    Test to check if compute correctly general rate if quality rate are missing..
    Final Rate = Func Rate + App Rate
    """
    pass


@pytest.mark.xfail(reason='Develop')
def test_general_rate_without_functionality():
    """
    Test to check if compute correctly general rate if functionality rate are missing..
    Final Rate = Quality Rate + App Rate
    """
    pass


@pytest.mark.xfail(reason='Develop')
def test_general_rate_without_appearance():
    """
    Test to check if compute correctly general rate if appearance rate are missing..
    Final Rate = Quality Rate + Functionality Rate
    """
    pass


@pytest.mark.xfail(reason='Develop')
def test_general_rate_without_quality():
    """
    Test to check if compute correctly general rate if quality rate are missing..
    Final Rate = Func Rate + App Rate
    """
    pass


# QUALITY RATE TEST CODE


@pytest.mark.xfail(reason='Develop')
def test_quality_rate():
    """
    Quality Rate Test
    Test to check all quality aspects, we suppose that we have full snapshot with all information and benchmarks
    """
    pass


@pytest.mark.xfail(reason='Develop')
def test_component_rate_equal_to_zero():
    """
    Quality Rate Test
    Test to check quality aspects with some fields equal to 0 or null
    """
    pass


# FUNCTIONALITY RATE TEST DONE


@pytest.mark.xfail(reason='Develop')
def test_functionality_rate():
    """
    Functionality Rate Test
    Tests to check all aspects of functionality, we assume we have a complete snapshot with all the information and tests performed.a
    """
    pass


@pytest.mark.xfail(reason='Develop')
def test_functionality_rate_miss_tests():
    """
    Functionality Rate Test
    Test to check if functionality rate compute correctly with some test without any information.
    """
    pass


@pytest.mark.xfail(reason='Discuss')
def test_appearance_rate():
    """
    Test to check if compute correctly a new rate of a device, only with visual test
    """
    pass


@pytest.mark.xfail(reason='Discuss')
def test_update_rate_with_manual_rate():
    """
    Test to check if compute correctly a new rate of a device, if this device input after a manual rate (like visual test)
    Computing a new rate with old snapshot information score and aggregate a new test information score.
    """
    pass

