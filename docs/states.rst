States
######
.. note:: In construction.

A mutable property of a device result of applying an
:ref:`actions:Action` to it.

States are represented as properties in :ref:`devices:Device` and
sub–types. They can be steps in a workflow
(like ``sold`` and ``payed``, part of a trading), or properties
describing computed values from applying events (like a list of owners,
or a quality rating).

There are three types of states:

* **Trading**: a workflow of states resulting from applying the action
  :ref:`actions:Trade`.
* **Physical**: a workflow of states resulting from applying
  physical actions (ref. :ref:`actions:Actions`).
* **Attributes**: miscellaneous device properties that are not part of
  a workflow.

.. uml:: states.puml

Trading
*******
 Trading states.

:cvar Reserved: The device has been reserved.
:cvar Cancelled: The device has been cancelled.
:cvar Sold: The device has been sold.
:cvar Donated: The device is donated.
:cvar Renting: The device is in renting
:cvar ToBeDisposed: The device is disposed.
      This is the end of life of a device.
:cvar ProductDisposed: The device has been removed
      from the facility. It does not mean end-of-life.

Physical
********
 Physical states.

:cvar ToBeRepaired: The device has been selected for reparation.
:cvar Repaired: The device has been repaired.
:cvar Preparing: The device is going to be or being prepared.
:cvar Prepared: The device has been prepared.
:cvar Ready: The device is in working conditions.
:cvar InUse: The device is being reported to be in active use.
