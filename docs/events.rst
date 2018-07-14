Events
######

..  toctree::
:maxdepth: 4

        event-diagram


Rate
****
Devicehub generates an rating for a device taking into consideration the
visual, functional, and performance.

.. todo:: add performance as a result of component fusion + general
tests in `here <https://github.com/eReuse/Rdevicescore/blob/master/
   img/input_process_output.png>`_.

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

.. todo:: which info does photobox provide for each picture?

Price
*****
Price states a selling price for the device, but not necessariliy the
final price this was sold (which is set in the Sell event).

Devicehub automatically computes a price from ``AggregateRating``
events. As in a **Rate**, price can have **software** and **version**,
and there is an **official** price that is used to automatically
compute the price from an ``AggregateRating``. Only the official price
is computed from an ``AggregateRating``.

Snapshot
********
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
========================
When processing a device from the Workbench, this one performs a Snapshot
and then performs more events (like testings, benchmarking...).

There are two ways of sending this information. In an async way,
this is, submitting events as soon as Workbench performs then, or
submitting only one Snapshot event with all the other events embedded.

Asynced
-------
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
------
Optionally, Devicehub understands receiving a ``Snapshot`` with all
the events in an ``events`` property inside each affected ``component``
or ``device``.

ToDispose and DisposeProduct
****************************
There are four events for getting rid of devices:

- ``ToDispose``: The device is marked to be disposed.
- ``DisposeProduct``: The device has been disposed. This is a ``Trade``
  event, which means that you can optionally ``DisposeProduct``
  to someone.
- ``RecyclingCenter`` have two extra special events:
    - ``DisposeWaste``: The device has been disposed in an unspecified
      manner.
    - ``Recover``: The device has been scrapped and its materials have
      been recovered under a new product.

.. note:: For usability purposes, users might not directly perform
``Dispose``, but this could automatically be done when
   performing ``ToDispose`` + ``Receive`` to a ``RecyclingCenter``.

.. todo:: Ensure that ``Dispose`` is a ``Trade`` event. An Org could
``Sell`` or ``Donate`` a device with the objective of disposing them.
    Is ``Dispose`` ok, or do we want to keep that extra ``Sell`` or
    ``Donate`` event? Could dispose be a synonym of any of those?
