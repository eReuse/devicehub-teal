from contextlib import suppress
from distutils.version import StrictVersion
from typing import Set, Union

from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.enums import RatingSoftware
from ereuse_devicehub.resources.event.models import AggregateRate, EreusePrice, Rate, \
    WorkbenchRate
from ereuse_devicehub.resources.event.rate.workbench import v1_0

RATE_TYPES = {
    WorkbenchRate: {
        RatingSoftware.ECost: {
            '1.0': v1_0.Rate()
        },
        RatingSoftware.EMarket: {
        }
    }
}


def rate(device: Device, rate: Rate):
    """
    Rates the passed-in ``rate`` using values from the rate itself
    and the ``device``.

    This method mutates ``rate``.

    :param device: The device to use as a model.
    :param rate: A half-filled rate.
    """
    cls = rate.__class__
    assert cls in RATE_TYPES, 'Rate type {} not supported.'.format(cls)
    assert rate.software in RATE_TYPES[cls], 'Rate soft {} not supported.'.format(rate.software)
    assert str(rate.version) in RATE_TYPES[cls][rate.software], \
        'Rate version {} not supported.'.format(rate.version)
    RATE_TYPES[cls][rate.software][str(rate.version)].compute(device, rate)


def main(rating_model: WorkbenchRate,
         software: RatingSoftware,
         version: StrictVersion) -> Set[Union[WorkbenchRate, AggregateRate, EreusePrice]]:
    """
    Generates all the rates (per software and version) for a given
    half-filled rate acting as a model, and finally it generates
    an ``AggregateRating`` with the rate that matches the
    ``software`` and ``version``.

    This method mutates ``rating_model`` by fulfilling it and
    ``rating_model.device`` by adding the new rates.

    :return: A set of rates with the ``rate`` value computed, where
             the first rate is the ``rating_model``.
    """
    assert rating_model.device
    events = set()
    for soft, value in RATE_TYPES[rating_model.__class__].items():
        for vers, func in value.items():
            if not rating_model.rating:  # Fill the rating before creating another rate
                rating = rating_model
            else:  # original rating was filled already; use a new one
                rating = WorkbenchRate(
                    labelling=rating_model.labelling,
                    appearance_range=rating_model.appearance_range,
                    functionality_range=rating_model.functionality_range,
                    device=rating_model.device,
                )
            rating.software = soft
            rating.version = vers
            rate(rating_model.device, rating)
            events.add(rating)
            if soft == software and vers == version:
                aggregation = AggregateRate.from_workbench_rate(rating)
                events.add(aggregation)
                with suppress(ValueError):
                    # We will have exception if range == VERY_LOW
                    events.add(EreusePrice(aggregation))
    return events
