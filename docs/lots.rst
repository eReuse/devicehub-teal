Lots
####

Lots are folders that contain devices and other lots, and can be
at the same time under several lots.

`Here <https://www.bustawin.com/
dags-with-materialized-paths-using-postgres-ltree/>`_ you have
a low-level technical implementation of how lots and their
relationships are mapped.

Getting lots
************

You can get lots list by ``GET /lots/``
There are one optional filter ``type``, only works with this 3 values ``temporary``, ``incoming`` and ``outgoing``

Create lots
***********
You create a lot by ``POST /lots/`` a `JSON Lot object <https://
app.swaggerhub.com/apis/ereuse/devicehub/0.2/#model-Lot>`_.

Adding / removing children
**************************
You can add lots to a lot by performing
``POST /lots/<parent-lot-id>/children/?id=<child-lot-1>&id=<child-lot-2>``.
Note that all lots must exist before. The **parent** lot is the
lot containing the **children** lots without any intermediate lot.

To remove children lots the idea is the same:
``DELETE /lots/<parent-lot-id>/children/?id=<child-lot-1>&id=<child-lot-2>``.

And for devices is all the same:
``POST /lots/<parent-lot-id>/devices/?id=<device-id-1>&id=<device-id-2>``;
idem for removing devices.

Sharing lots
************
Sharing a lot means giving certain permissions to users, like reading
the characteristics of devices, or performing certain events.

Linking lots
============
Linking lots means setting a reference to a lot in another Devicehub
which supposedly have the same devices. One of both lots is considered
to be the outgoing lot and the other one the ingoing, in the sense
that the lifetime of the devices of the outgoing lot precedes the
incoming lot; in other way, the events of the devices in the outgoing
lot should (but not enforced) happen before that the events in the
incoming lot.

The lot has two fields that uses to keep a link: the Devicehub URL and
the ID of the other lot (internal ID I suppose...).

A device can only be in one incoming lot and in one outgoing lot.

A device inside a linked lot, when it is confirmed the existence of
an equal device in the other DB, is considered to be linked.

A linked lot defines a both way share of READ Characteristics, at
least.

Users can sync the characteristics of devices + selected tags + selected rules,
copying (but not deleting) devices between them. This ensures no
traceability warnings when generating the lifetime of devices. In first
iterations this process could be done manually (to allow user select
tags and rules)


Why linking lots
----------------

* Get the lifetime of devices (reporting). This way a Devicehub
  traverses the linked devices (as long as it has perm).
* Send devices to another Devicehub (characteristics).
* Ensure rules over linked devices.
