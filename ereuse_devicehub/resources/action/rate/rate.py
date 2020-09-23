import math
from typing import Iterable

from ereuse_devicehub.resources.device.models import Device


class BaseRate:
    """Growing exponential from this value."""
    CEXP = 0
    """Growing lineal starting on this value."""
    CLIN = 242
    """Growing logarithmic starting on this value."""
    CLOG = 0.5

    """Processor has 50% of weight over total score, used in harmonic mean."""
    PROCESSOR_WEIGHT = 0.5
    """Storage has 20% of weight over total score, used in harmonic mean."""
    DATA_STORAGE_WEIGHT = 0.2
    """Ram has 30% of weight over total score, used in harmonic mean."""
    RAM_WEIGHT = 0.3

    def compute(self, device: Device):
        raise NotImplementedError()

    @staticmethod
    def norm(x, x_min, x_max):
        return (x - x_min) / (x_max - x_min)

    @staticmethod
    def rate_log(x):
        return math.log10(2 * x) + 3.57  # todo magic number!

    @staticmethod
    def rate_lin(x):
        return 7 * x + 0.06  # todo magic number!

    @staticmethod
    def rate_exp(x):
        return math.exp(x) / (2 - math.exp(x))

    @staticmethod
    def harmonic_mean(weights: Iterable[float], rates: Iterable[float]):
        return sum(weights) / sum(char / rate for char, rate in zip(weights, rates))

    def harmonic_mean_rates(self, rate_processor, rate_storage, rate_ram):
        """Merging components using harmonic formula."""
        total_weights = self.PROCESSOR_WEIGHT + self.DATA_STORAGE_WEIGHT + self.RAM_WEIGHT
        total_rate = self.PROCESSOR_WEIGHT / rate_processor \
                     + self.DATA_STORAGE_WEIGHT / rate_storage \
                     + self.RAM_WEIGHT / rate_ram
        return total_weights / total_rate
