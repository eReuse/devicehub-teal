Actions and states
##################

Actions are events performed to devices, changing their **state**.
Actions can have attributes defining
**where** it happened, **who** performed them, **when**, etc.
Actions are stored in a log for each device. An exemplifying action
can be ``Repair``, which dictates that a device has been repaired,
after this action, the device is in the ``repaired`` state.

Actions and states affect devices in different ways or **dimensions**.
For example, ``Repair`` affects the **physical** dimension of a device,
and ``Sell`` the **political** dimension of a device. A device
can be in several states at the same time, one per dimension; ie. a
device can be ``repaired`` (physical) and ``reserved`` (political),
but not ``repaired`` and ``disposed`` at the same time.

Devicehub actions inherit from `schema actions
<http://schema.org/Action>`_, are written in Pascal case and using
a verb in infinitive. Some verbs represent the willingness or
assignment to perform an action; ``ToRepair`` states that the device
is going to be / must be repaired, whereas ``Repair`` states
that the reparation happened. The former actions have the preposition
*To* prefixing the verb.

In the following section we define the actions and states.
To see how to perform actions to the Devicehub API head
to the `Swagger docs
<https://app.swaggerhub.com/apis/ereuse/devicehub/0.2>`_.

..  toctree::
    :maxdepth: 4

    actions

.. uml:: actions.puml


Physical Actions
****************
The following actions describe and react on the
:class:`ereuse_devicehub.resources.device.states.Physical` condition
of the devices.

ToPrepare, Prepare
==================
.. autoclass:: ereuse_devicehub.resources.event.models.Prepare
.. autoclass:: ereuse_devicehub.resources.event.models.ToPrepare

ToRepair, Repair
================
.. autoclass:: ereuse_devicehub.resources.event.models.Repair
.. autoclass:: ereuse_devicehub.resources.event.models.ToRepair

ReadyToUse
==========
.. autoclass:: ereuse_devicehub.resources.event.models.ReadyToUse

Live
====
.. autoclass:: ereuse_devicehub.resources.event.models.Live

DisposeWaste, Recover
=====================
``RecyclingCenter`` users have two extra special events:
    - ``DisposeWaste``: The device has been disposed in an unspecified
      manner.
    - ``Recover``: The device has been scrapped and its materials have
      been recovered under a new product.

See `ToDisposeProduct, DisposeProduct`_.

.. todo:: Events not developed yet.

Association actions
*******************
Actions that change the associations users have with devices;
ie. the **owners**, **usufructuarees**, **reservees**,
and **physical possessors**.

There are three sub-dimensions: **trade**, **transfer**,
and **organize** actions.

.. uml:: association-events.puml

Trade actions
=============
Not fully developed.
.. autoclass:: ereuse_devicehub.resources.event.models.Trade

Sell
----
.. autoclass:: ereuse_devicehub.resources.event.models.Sell

Donate
------
.. autoclass:: ereuse_devicehub.resources.event.models.Donate

Rent
----
.. autoclass:: ereuse_devicehub.resources.event.models.Rent

CancelTrade
-----------
.. autoclass:: ereuse_devicehub.resources.event.models.CancelTrade

ToDisposeProduct, DisposeProduct
--------------------------------
.. autoclass:: ereuse_devicehub.resources.event.models.DisposeProduct
.. autoclass:: ereuse_devicehub.resources.event.models.ToDisposeProduct

Transfer actions
================
The act of transferring/moving devices from one place to another.

Receive
-------
.. autoclass:: ereuse_devicehub.resources.event.models.Receive
.. autoclass:: ereuse_devicehub.resources.enums.ReceiverRole
    :members:
    :undoc-members:
.. autoattribute:: ereuse_devicehub.resources.device.models.Device.physical_possessor

Organize actions
================
.. autoclass:: ereuse_devicehub.resources.event.models.Organize

Reserve, CancelReservation
-------------------------
Not fully developed.

.. autoclass:: ereuse_devicehub.resources.event.models.Reserve
.. autoclass:: ereuse_devicehub.resources.event.models.CancelReservation

Assign, Accept, Reject
----------------------
Not developed.

``Assign`` allocates devices to an user. The purpose or meaning
of the association is defined by the users.

``Accept`` and ``Reject`` allow users to accept and reject the
assignments.

.. todo:: shall we add ``Deassign`` or make ``Assign``
   always define all active users?
   Assign won't be developed until further notice.

Internal state actions
**********************
Actions providing metadata about devices that don't usually change
their state.

Snapshot
========
.. autoclass:: ereuse_devicehub.resources.event.models.Snapshot


Add, Remove
===========
.. autoclass:: ereuse_devicehub.resources.event.models.Add
.. autoclass:: ereuse_devicehub.resources.event.models.Remove

Erase
=====
.. autoclass:: ereuse_devicehub.resources.event.models.EraseBasic
.. autoclass:: ereuse_devicehub.resources.event.models.EraseSectors
.. autoclass:: ereuse_devicehub.resources.enums.ErasureStandards
    :members:
.. autoclass:: ereuse_devicehub.resources.event.models.ErasePhysical
.. autoclass:: ereuse_devicehub.resources.enums.PhysicalErasureMethod
    :members:
    :undoc-members:


Install
=======
.. autoclass:: ereuse_devicehub.resources.event.models.Install

Test
====
.. autoclass:: ereuse_devicehub.resources.event.models.Test

TestDataStorage
---------------
.. autoclass:: ereuse_devicehub.resources.event.models.TestDataStorage

StressTest
----------
.. autoclass:: ereuse_devicehub.resources.event.models.StressTest

Benchmark
=========
.. autoclass:: ereuse_devicehub.resources.event.models.Benchmark


BenchmarkDataStorage
--------------------
.. autoclass:: ereuse_devicehub.resources.event.models.BenchmarkDataStorage


BenchmarkWithRate
-----------------
.. autoclass:: ereuse_devicehub.resources.event.models.BenchmarkWithRate


BenchmarkProcessor
------------------
.. autoclass:: ereuse_devicehub.resources.event.models.BenchmarkProcessor


BenchmarkProcessorSysbench
--------------------------
.. autoclass:: ereuse_devicehub.resources.event.models.BenchmarkProcessorSysbench


BenchmarkRamSysbench
--------------------
.. autoclass:: ereuse_devicehub.resources.event.models.BenchmarkRamSysbench

Rate
====
.. autoclass:: ereuse_devicehub.resources.event.models.Rate

The following are the values the appearance, performance, and
functionality grade can have:

.. autoclass:: ereuse_devicehub.resources.enums.AppearanceRange
    :members:
    :undoc-members:
.. autoclass:: ereuse_devicehub.resources.enums.FunctionalityRange
    :members:
    :undoc-members:
.. autoclass:: ereuse_devicehub.resources.enums.RatingRange

Price
=====
.. autoclass:: ereuse_devicehub.resources.event.models.Price

Migrate
=======
Not done.

.. autoclass:: ereuse_devicehub.resources.event.models.Migrate

Locate
======
todo
.. todo !!


States
******
.. autoclass:: ereuse_devicehub.resources.device.states.State

.. uml:: states.puml

.. autoclass:: ereuse_devicehub.resources.device.states.Trading
    :members:
    :undoc-members:
.. autoclass:: ereuse_devicehub.resources.device.states.Physical
    :members:
    :undoc-members:
