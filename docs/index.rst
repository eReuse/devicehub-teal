.. title:: DeviceHub

.. image:: https://www.ereuse.org/files/2017/04/DeviceHub-logo-V2.svg
   :height: 100px
   :alt: DeviceHub logo


This is the documentation of the `eReuse.org Devicehub
<https://github.com/ereuse/devicehub-teal>`_.

Devicehub is a distributed IT Asset Management System focused in
reusing devices, created under the project
`eReuse.org <https://www.ereuse.org>`_.

Our main objectives are:

- To offer a common IT Asset Management for distributors, refurbishers,
  receivers and other IT professionals so they can manage devices and exchange them.
  This is, reusing —and ultimately recycling.
- To automatically recollect, analyse, process and share
  (controlling privacy) metadata about devices with other tools of the
  eReuse ecosystem to guarantee traceability, and to provide inputs for
  the indicators which measure circularity.

The main entity of a Devicehub are :ref:`devices:Devices`, which is any object that
can be identified. Devices are divided in *types* (like ``Computer``),
and each one defines *properties*, like serial number, weight,
quality rating, pricing, or a list of owners.

We perform :ref:`actions:Actions` on devices, which are events that
change their *state* and *properties*. Examples are sales, reparations,
quality diagnostics, data wiping, and location.
Actions are stored in the traceability log of the device.

Devicehub is decentralized, and each instance is an inventory. We can
share and exchange devices between inventories —like in real live between
organizations.

:ref:`tags:Tags` identify devices through those organizations and their
internal systems. With Devicehub we can manage and print smart tags with
QR and NFC capabilities, operating devices by literally scanning them.

Devicehub is a REST API built with `Teal <https://github.com/ereuse/teal>`_ and
`Flask <http://flask.pocoo.org>`_ using `PostgreSQL <https://www.postgresql.org>`_.
`DevicehubClient <https://github.com/ereuse/devicehubclient>`_ is the
front–end that consumes this API.

..  toctree::
    :maxdepth: 2

    api
    devices
    actions
    states
    tags
    lots

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
