Devices
#######
Devices are objects that can be identified, and they are the
main entity in a Devicehub. Refer to :ref:`devices:Device` for more
info.

Schema
******
The following schema represents all the device types and their
properties.

.. dhlist::
    :module: ereuse_devicehub.resources.device.schemas

API
***
You can retrieve devices using ``GET /devices/``, or a specific
device by ``GET /devices/24``.

You can **filter** devices ``GET /devices/?filter={"type": "Computer"}``,
**sort** them ``GET /devices/?sort={"created": 1}``, and perform
natural search with ``GET /devices/?search=foo bar. Of course
you can combine them in the same query, returning devices that
only pass all conditions.

Results are **paginated**; you get up to 30 devices and up to 30
groups in a page. Select the actual page by ``GET /inventory?page=3``.
By default you get the page number ``1``.

Query
*****
The query consists of 4 optional params:

- **search**: Filters devices by performing a full-text search over their
  physical properties, events, and tags. Search is a string.
- **filter**: Filters devices field-by-field. Each field can be
  filtered in different ways, see them in
  :class:`ereuse_devicehub.resources.devices.Filters`. Filter is
  a JSON-encoded object whose keys are the filters. By default
  is empty (no filter applied).
- **sort**: Sorts the devices. You can specify multiple sort clauses
  as it is a JSON-encoded object whose keys are fields and values
  are truthy for *ascending* order, or falsy for *descending* order.
  By default it is sorted by ``Device.created`` descending (newest
  devices first).
- **page**: A natural number that specifies the page to retrieve.
  By default is ``1``; the first page.

Result
******
The result is a JSON object with the following fields:

- **items**: A list of devices.
- **pagination**:
  - **page**: The page you requested in the ``page`` param of the query,
    or ``1``.
  - **perPage**: How many devices are in every page, fixed to ``30``.
  - **total**: How many total devices passed the filters.
  - **next**: The number of the next page, if any.
  - **last**: The number of the last page, if any.


