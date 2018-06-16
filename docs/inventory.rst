Inventory
#########

Devicehub uses the same path to get devices and lots.

To get all devices and groups: ``GET /inventory`` or the devices of a
specific groups: ``GET /inventory/24``.

You can **filter** devices ``GET /inventory/24?filter={"type": "Computer"}``,
and **sort** them ``GET /inventory?sort={"created": 1}``, and of course
you can combine both in the same query. You only get the groups that
contain the devices that pass the filters. So, if a group contains
only one device that is filtered, you don't get that group neither.

Results are **paginated**; you get up to 30 devices and up to 30
groups in a page. Select the actual page by ``GET /inventory?page=3``.
By default you get the page number ``1``.

Query
*****
The query consists of 4 optional params:

- **search**: Filters devices by performing a full-text search over their
  physical properties, events, tags, and groups they are in:

    - Device.type
    - Device.serial_number
    - Device.model
    - Device.manufacturer
    - Device.color
    - Tag.id
    - Tag.org
    - Group.name

  Search is a string.
- **filter**: Filters devices field-by-field. Each field can be
  filtered in different ways, see them in
  :class:`ereuse_devicehub.resources.inventory.Filters`. Filter is
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

- **devices**: A list of devices.
- **groups**: A list of groups.
- **widgets**: A dictionary of widgets.
- **pagination**: Pagination information:

  - **page**: The page you requested in the ``page`` param of the query,
    or ``1``.
  - **perPage**: How many devices are in every page, fixed to ``30``.
  - **total**: How many total devices passed the filters.
