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
The following actions describe and react on the physical condition
of the devices.

ToPrepare, Prepare
==================
Work has been performed to the device to a defined point of
acceptance. Users using this event have to agree what is this point
of acceptance; for some is when the device just works, for others
when some testing has been performed.

**Prepare** dictates that the device has been prepared, whereas
**ToPrepare** that the device has been selected to be prepared.

Usually **ToPrepare** is the next event done after registering the
device.

ToRepair, Repair
================
ToRepair is the act of selecting a device to be repaired, and
Repair the act of performing the actual reparations. If a repair
without an error is performed, it represents that the reparation
has been successful.

ReadyToUse
==========
The device is ready to be used. This involves greater preparation
from the ``Prepare`` event, and users should only use a device
after this event is performed.

Users usually require devices with this event before shipping them
to costumers.

Live
====
A keep-alive from a device connected to the Internet with information
about its state (in the form of a ``Snapshot`` event) and usage
statistics.

DisposeWaste, Recover
=====================
``RecyclingCenter`` users have two extra special events:
    - ``DisposeWaste``: The device has been disposed in an unspecified
      manner.
    - ``Recover``: The device has been scrapped and its materials have
      been recovered under a new product.

See `ToDisposeProduct, DisposeProduct`_.

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
Trade actions log the political exchange of devices between users,
stating **owner** xor **usufructuaree**. Every time a trade event
is performed, the old user looses its political possession in favor
of another one.

Sell
----
The act of taking money from a buyer in exchange of a device.

Donate
------
The act of giving devices without compensation.

Rent
----
The act of giving money in return for temporary use, but not
ownership, of a device.

CancelTrade
-----------
The act of cancelling a `Sell`_, `Donate`_ or `Rent`_.

ToDisposeProduct, DisposeProduct
-------------------------
``ToDispose`` and ``DisposeProduct`` manage the process of getting
rid of devices by giving (selling, donating) to another organization
like a waste manager.

``ToDispose`` marks a device for being disposed, and
``DisposeProduct`` dictates that the device has been disposed.

See `DisposeWaste, Recover`_ events for disposing without trading
the device.

.. note:: For usability purposes, users might not directly perform
   ``Dispose``, but this could automatically be done when
   performing ``ToDispose`` + ``Receive`` to a ``RecyclingCenter``.

Transfer actions
================
The act of transferring/moving devices from one place to another.

Receive
-------
The act of physically taking delivery of a device. The receiver
confirms that the devices have arrived, and thus, they
**physically possess** them. Note that
there can only be one **physical possessor** per device, and
``Receive`` changes it.

The receiver can optionally take a role in the reception, giving
it meaning; an user that takes the ``FinalUser`` role in the
reception express that it will use the device, whereas a role
``Transporter`` is used by intermediaries in shipping.

.. todo:: how do we ensure users specify type of reception?

Organize actions
================
The act of manipulating/administering/supervising/controlling one or
more devices.

Reserve, CancelReservation
--------------------------
The act of reserving devices and cancelling them.

After this event is performed, the user is the **reservee** of the
devices. There can only be one non-cancelled reservation for
a device, and a reservation can only have one reservee.

Assign, Accept, Reject
----------------------
``Assign`` allocates devices to an user. The purpose or meaning
of the association is defined by the users.

``Accept`` and ``Reject`` allow users to accept and reject the
assignments.

.. todo:: shall we add ``Deassign`` or make ``Assign``
   always define all active users?

.. todo:: Assign won't be developed until further notice.


Internal state actions
**********************
Actions providing metadata about devices that don't usually change
their state.

Snapshot
========
The Snapshot sets the physical information of the device (S/N, model...)
and updates it with erasures, benchmarks, ratings, and tests; updates the
composition of its components (adding / removing them), and links tags
to the device.

When receiving a Snapshot, the DeviceHub creates, adds and removes
components to match the Snapshot. For example, if a Snapshot of a computer
contains a new component, the system searches for the component in its
database and, if not found, its creates it; finally linking it to the
computer.

A Snapshot is used with Remove to represent changes in components for
a device:

1. ``Snapshot`` creates a device if it does not exist, and the same
   for its components. This is all done in one ``Snapshot``.
2. If the device exists, it updates its component composition by
   *adding* and *removing* them. If,
   for example, this new Snasphot doesn't have a component, it means that
   this component is not present anymore in the device, thus removing it
   from it. Then we have that:

     - Components that are added to the device: snapshot2.components -
       snapshot1.components
     - Components that are removed to the device: snapshot1.components -
       snapshot2.components

   When adding a component, there may be the case this component existed
   before and it was inside another device. In such case, DeviceHub will
   perform ``Remove`` on the old parent.

Snapshots from Workbench
------------------------
When processing a device from the Workbench, this one performs a Snapshot
and then performs more events (like testings, benchmarking...).

There are two ways of sending this information. In an async way,
this is, submitting events as soon as Workbench performs then, or
submitting only one Snapshot event with all the other events embedded.

Asynced
^^^^^^^
The use case, which is represented in the ``test_workbench_phases``,
is as follows:

1. In **T1**, WorkbenchServer (as the middleware from Workbench and
   Devicehub) submits:

   - A ``Snapshot`` event with the required information to **synchronize**
     and **rate** the device. This is:

       - Identification information about the device and components
         (S/N, model, physical characteristics...)
       - ``Tags`` in a ``tags`` property in the ``device``.
       - ``Rate`` in an ``events`` property in the ``device``.
       - ``Benchmarks`` in an ``events`` property in each ``component``
         or ``device``.
       - ``TestDataStorage`` as in ``Benchmarks``.
   - An ordered set of **expected events**, defining which are the next
     events that Workbench will perform to the device in ideal
     conditions (device doesn't fail, no Internet drop...).

   Devicehub **syncs** the device with the database and perform the
   ``Benchmark``, the ``TestDataStorage``, and finally the ``Rate``.
   This leaves the Snapshot **open** to wait for the next events
   to come.
2. Assuming that we expect all events, in **T2**, WorkbenchServer
   submits a ``StressTest`` with a ``snapshot`` field containing the
   ID of the Snapshot in 1, and Devicehub links the event with such
   ``Snapshot``.
3. In **T3**, WorkbenchServer submits the ``Erase`` with the ``Snapshot``
   and ``component`` IDs from 1, linking it to them. It repeats
   this for all the erased data storage devices; **T3+Tn** being
   *n* the erased data storage devices.
4. WorkbenchServer does like in 3. but for the event ``Install``,
   finishing in **T3+Tn+Tx**, being *x* the number of data storage
   devices with an OS installed into.
5. In **T3+Tn+Tx**, when all *expected events* have been performed,
   Devicehub **closes** the ``Snapshot`` from 1.

Synced
^^^^^^
Optionally, Devicehub understands receiving a ``Snapshot`` with all
the events in an ``events`` property inside each affected ``component``
or ``device``.

Add, Remove
===========
The act of adding and removing components of and from a device.

These are usually used internally from `Snapshot`_, or manually, for
example, when removing a component (like a ``DataStorage`` unit) from
a broken computer.

EraseBasic, EraseSectors
========================
An erasure attempt to a ``DataStorage``. The event contains
information about success and nature of the erasure.

``EraseBasic`` is a fast non-secured way of erasing data storage, and
``EraseSectors`` is a slower secured, sector-by-sector, erasure
method.

Users can generate erasure certificates from successful erasures.

Erasures are an accumulation of **erasure steps**, that are performed
as separate actions, called ``StepRandom``, for an erasure step
that has overwritten data with random bits, and ``StepZero``,
for an erasure step that has overwritten data with zeros.

Install
=======
The action of install an Operative System to a data storage unit.

Test
====
The act of testing the physical condition of a device and its
components.

TestDataStorage
---------------
The act of testing the data storage.

Testing is done using the `S.M.A.R.T self test
<https://en.wikipedia.org/wiki/S.M.A.R.T.#Self-tests>`_. Note
that not all data storage units, specially some new PCIe ones, do not
support SMART testing.

The test takes to other SMART values indicators of the overall health
of the data storage.

StressTest
----------
The act of stressing (putting to the maximum capacity)
a device for an amount of minutes. If the device is not in great
condition won't probably survive such test.

Benchmark
=========
The act of gauging the performance of a device.

BenchmarkDataStorage
--------------------
Benchmarks the data storage unit reading and writing speeds.

BenchmarkWithRate
-----------------
The act of benchmarking a device with a single rate.

BenchmarkProcessor
------------------
Benchmarks a processor by executing `BogoMips
<https://en.wikipedia.org/wiki/BogoMips>`_. Note that this is not
a reliable way of rating processors and we keep it for compatibility
purposes.

BenchmarkProcessorSysbench
--------------------------
Benchmarks a processor by using the processor benchmarking utility of
`sysbench <https://github.com/akopytov/sysbench>`_.


Rate
====
Devicehub generates an rating for a device taking into consideration the
visual, functional, and performance.

A Workflow is as follows:

1. An agent generates feedback from the device in the form of benchmark,
   visual, and functional information; which is filled in a ``Rate``
   event. This is done through a **software**, defining the type
   of ``Rate`` event. At the moment we have two rates: ``WorkbenchRate``
   and ``PhotoboxRate``.
2. Devicehub gathers this information and computes a score that updates
   the ``Rate`` event.
3. Devicehub aggregates different rates and computes a final score for
   the device by performing a new ``AggregateRating`` event.

There are three **types** of ``Rate``: ``WorkbenchRate``,
``AppRate``, and ``PhotoboxRate``. ``WorkbenchRate`` can have different
**software** algorithms, and each software algorithm can have several
**versions**. So, we have 3 dimensions for ``WorkbenchRate``:
type, software, version.

Devicehub generates a rate event for each software and version. So,
if an agent fulfills a ``WorkbenchRate`` and there are 2 software
algorithms and each has two versions, Devicehub will generate 4 rates.
Devicehub understands that only one software and version are the
**oficial** (set in the settings of each inventory),
and it will generate an ``AggregateRating`` for only the official
versions. At the same time, ``Price`` only computes the price of
the **oficial** version.

The technical Workflow in Devicehub is as follows:

1. In **T1**, the user performs a ``Snapshot`` by processing the device
   through the Workbench. From the benchmarks and the visual and
   functional ratings the user does in the device, the system generates
   many ``WorkbenchRate`` (as many as software and versions defined).
   With only this information, the system generates an ``AggregateRating``,
   which is the event that the user will see in the web.
2. In **T2**, the user takes pictures from the device through the
   Photobox, and DeviceHub crates an ``ImageSet`` with multiple
   ``Image`` with information from the photobox.
3. In **T3**, an agent (user or AI) rates the pictures, creating a
   ``PhotoboxRate`` **for each** picture. When Devicehub receives the
   first ``PhotoboxRate`` it creates an ``AggregateRating`` linked
   to such ``PhotoboxRate``. So, the agent will perform as many
   ``PhotoboxRate`` as pictures are in the ``ImageSet``, and Devicehub
   will link each ``PhotoboxRate`` to the same ``AggregateRating``.
   This will end in **T3+Tn**, being *n* the number of photos to rate.
4. In **T3+Tn**, after the last photo is rated, Devicehub will generate
   a new rate for the device: it takes the ``AggregateRating`` from 3.
   and computes a rate from all the linked ``PhotoboxRate`` plus the
   last available ``WorkbenchRate`` for that device.

If the agent in 3. is an user, Devicehub creates ``PhotoboxUserRate``
and if it is an AI it creates ``PhotoboxAIRate``.

The same ``ImageSet`` can be rated multiple times, generating a new
``AggregateRating`` each time.

Price
=====
Price states a selling price for the device, but not necessariliy the
final price this was sold (which is set in the Sell event).

Devicehub automatically computes a price from ``AggregateRating``
events. As in a **Rate**, price can have **software** and **version**,
and there is an **official** price that is used to automatically
compute the price from an ``AggregateRating``. Only the official price
is computed from an ``AggregateRating``.

Migrate
=======
Moves the devices to a new database/inventory. Devices cannot be
modified anymore at the previous database.

Donation
========
.. todo:: nextcloud/eReuse/99. Tasks/224. Definir datos necesarios
   configuración licencia


States
******
.. todo:: work on september.

.. uml:: states.puml

