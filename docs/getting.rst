Getting
=======

Devicehub uses the same path to get devices and lots.

To get the lot information ::

    GET /inventory/24

You can specifically filter devices::

    GET /inventory?devices?
    GET /inventory/24?type=24&type=44&status={"name": "Reserved", "updated": "2018-01-01"}
    GET /inventory/25?price=24&price=21

GET /devices/4?

Returns devices that matches the filters and the lots that contain them.
If the filters are applied to the lots, it returns the matched lots
and the devices that contain them.
You can join filters.

