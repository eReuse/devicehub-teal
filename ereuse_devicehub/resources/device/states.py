from enum import Enum

import inflection

from ereuse_devicehub.resources.action import models as e


class State(Enum):
    """A mutable property of a device result of applying an
    :ref:`actions:Action` to it.
    """

    @classmethod
    def actions(cls):
        """Actions participating in this state."""
        return (s.value for s in cls)

    def __str__(self):
        return inflection.humanize(inflection.underscore(self.name))


class Trading(State):
    """Trading states.

    :cvar Reserved: The device has been reserved.
    :cvar Cancelled: The device has been cancelled.
    :cvar Sold: The device has been sold.
    :cvar Donated: The device is donated.
    :cvar Renting: The device is in renting
    :cvar ToBeDisposed: The device is disposed.
          This is the end of life of a device.
    :cvar ProductDisposed: The device has been removed
          from the facility. It does not mean end-of-life.
    """
    Reserved = e.Reserve
    Cancelled = e.CancelTrade
    Sold = e.Sell
    Donated = e.Donate
    Renting = e.Rent
    # todo add Pay = e.Pay
    ToBeDisposed = e.ToDisposeProduct
    ProductDisposed = e.DisposeProduct
    Available = e.MakeAvailable


class Physical(State):
    """Physical states.

    :cvar ToBeRepaired: The device has been selected for reparation.
    :cvar Repaired: The device has been repaired.
    :cvar Preparing: The device is going to be or being prepared.
    :cvar Prepared: The device has been prepared.
    :cvar Ready: The device is in working conditions.
    """
    ToBeRepaired = e.ToRepair
    Repaired = e.Repair
    Preparing = e.ToPrepare
    Prepared = e.Prepare
    Ready = e.Ready


class Traking(State):
    """Traking states.

    :cvar Receive: The device changes hands
    """
    # Receive = e.Receive
    pass

    
class Usage(State):
    """Usage states.

    :cvar Allocate: The device is allocate in other Agent (organization, person ...)
    :cvar Deallocate: The device is deallocate and return to the owner
    :cvar InUse: The device is being reported to be in active use. 
    """
    Allocate = e.Allocate
    Deallocate = e.Deallocate
    InUse = e.Live
