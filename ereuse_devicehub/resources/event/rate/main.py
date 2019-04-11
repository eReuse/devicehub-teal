from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.event.models import RateComputer
from ereuse_devicehub.resources.event.rate.workbench import v1_0

RATE_TYPES = {
    RateComputer: {
        '1.0': v1_0.Rate()
    }
}


def rate(device: Device, version):
    """
    Rates the passed-in ``rate`` using values from the rate itself
    and the ``device``.

    This method mutates ``rate``.

    :param device: The device to use as a model.
    :param rate: A half-filled rate.
    """
    assert cls in RATE_TYPES, 'Rate type {} not supported.'.format(cls)
    assert str(rate.version) in RATE_TYPES[cls], \
        'Rate version {} not supported.'.format(rate.version)
    RATE_TYPES[cls][str(rate.version)].compute(device)
