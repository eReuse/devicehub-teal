Actions and states
##################

Actions
*******

Actions are events performed to devices, changing their **state**.
Actions can have attributes defining
**where** it happened, **who** performed them, **when**, etc.
Actions are stored in a log for each device. An exemplifying action
can be ``Repair``, which dictates that a device has been repaired,
after this action, the device is in the ``repaired`` state.

Devicehub actions inherit from `schema actions
<http://schema.org/Action>`_, are written in Pascal case and using
a verb in infinitive. Some verbs represent the willingness or
assignment to perform an action; ``ToRepair`` states that the device
is going to be / must be repaired, whereas ``Repair`` states
that the reparation happened. The former actions have the preposition
*To* prefixing the verb.

Actions and states affect devices in different ways or **dimensions**.
For example, ``Repair`` affects the **physical** dimension of a device,
and ``Sell`` the **political** dimension of a device. A device
can be in several states at the same time, one per dimension; ie. a
device can be ``repaired`` (physical) and ``reserved`` (political),
but not ``repaired`` and ``disposed`` at the same time:


- Physical actions: The following actions describe and react on the
  Physical condition of the devices.

  - ToPrepare and prepare.
  - ToRepair, Repair
  - ReadyToUse
  - Live
  - DisposeWaste, Recover

- Association actions: Actions that change the associations users have with devices;
  ie. the **owners**, **usufructuarees**, **reservees**,
  and **physical possessors**.

  - Trade
  - Transfer
  - Organize

- Internal state actions: Actions providing metadata about devices that don't usually change
  their state.

  - Snapshot
  - Add, remove
  - Erase
  - Install
  - Test
  - Benchmark
  - Rate
  - Price


The following index has all the actions (please note we are moving from calling them
``Event`` to call them ``Action``):

.. dhlist::
    :module: ereuse_devicehub.resources.event.schemas


States
******
.. autoclass:: ereuse_devicehub.resources.device.states.State

.. uml:: states.puml

.. autoclass:: ereuse_devicehub.resources.device.states.Trading
.. autoclass:: ereuse_devicehub.resources.device.states.Physical
