from enum import Enum

import inflection

from ereuse_devicehub.resources.event import models as e


class State(Enum):
    @classmethod
    def events(cls):
        """Events participating in this state."""
        return (s.value for s in cls)

    def __str__(self):
        return inflection.humanize(inflection.underscore(self.name))


class Trading(State):
    Reserved = e.Reserve
    Cancelled = e.CancelTrade
    Sold = e.Sell
    Donated = e.Donate
    Renting = e.Rent
    # todo add Pay = e.Pay
    ToBeDisposed = e.ToDisposeProduct
    ProductDisposed = e.DisposeProduct


class Physical(State):
    ToBeRepaired = e.ToRepair
    Repaired = e.Repair
    Preparing = e.ToPrepare
    Prepared = e.Prepare
    ReadyToBeUsed = e.ReadyToUse
    InUse = e.Live
