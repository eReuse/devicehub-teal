Tags
####
Devicehub can generate tags, which are synthetic identifiers that
identify a device in an organization. A tag has minimally two fields:
the ID and the Registration Number of the organization that generated
such ID.

In Devicehub tags are created empty, this is without any device
associated, and they are associated or **linked** when they are assigned
to a device. In Devicehub you usually use the AndroidApp to link
tags and devices.

The organization that created the tag in the Devicehub (which can be
impersonating the organization that generated the ID) is called the
**tag provider**. This is usual when dealing with other organizations
devices.

A device can have many tags but a tag can only be linked to one device.
As for the actual implementation, you cannot unlink them.

Devicehub users can design, generate and print tags, manually setting
an ID and a tag provider. Note though that these virtual tags don't have
to forcefully be printed or have a physical representation
(this is not imposed at system level).

Tags are case insensitive and are converted to lower-case in
Devicehub.

eTags
*****
We recognize a special type of tag, the **eReuse.org tags (eTag)**.
These are tags defined by eReuse.org and that can be issued only
by tag providers that comply with the eReuse.org requisites.

The eTags are designed to empower device exchange between
organizations and identification efficiency. They are built with durable
plastic and have a QR code, a NFC chip and a written ID.

These tags live in separate databases from Devicehubs, empowered by
the `eReuse.org Tag <https://github.com/ereuse/tag>`_ software.
By using this software, eReuse.org certified tag providers
can create and manage the tags, and send them to Devicehubs of their
choice.

The section *Use-case with eTags* shows the use-case of these
eTags.

Tag ID design
=============
The eTag has a fixed schema for its ID: ``XXX-YYYYYYYYYYYYYY``, where:

- *XX* is the **eReuse.org Tag Provider ID (eTagPId)**.
- *YYYYYYYYYYYY* is the ID of the tag in the provider..

The eTagPid identifies an official eReuse.org Tag provider; this ID
is managed by eReuse.org in a public repository. eTagPIds are made of
2 capital letters and numbers.

The ID of the tag in the provider (*YYYYYYYYYYYYYY*) consists from
5 to 10 capital letters and numbers (registering a maximum of 10^12
tags).

As an example, ``FO-A4CZ2`` is a tag from the ``FO`` tag provider
and ID ``A4CZ2``.

Creating tags
*************
You need to create a tag before linking it to a device. There are
two ways of creating a tag:

- By performing ``POST /tags?ids=...`` and passing a list of tag IDs
  to create. All users can create tags this method, however they
  cannot create eTags. Get more info at the endpoint docs.
- By executing in a terminal ``flask create-tags <ids>`` and passing
  a list of IDs to create. Only an admin is supposed to use this method,
  which allows them to create eTags. Get more info with
  ``flask create-tags --help``.

Note that tags cannot have a slash ``/``.

Linking a tag
*************
Linking a tag is joining the tag with the device.

In Devicehub this process is done when performing a Snapshot (POST
Snapshot), by setting tag ids in ``snapshot['device']['tags']``. Future
implementation will allow setting to the organization to ensure
tags are inequivocally correct.

Note that tags must exist in the database prior this.

You can only link once, and consecutive Snapshots that have the same
tag will validate that the link is correct –so it is good praxis to
try to always provide the tag when performing a Snapshot. Tags help
too in finding devices when these don't generate a ``HID``. Find more
in the ``Snapshot`` docs.

Getting a device through its tag
********************************
When performing ``GET /tags/<tag-id>/device`` you will get directly the
device of such tag, as long as there are not two tags with the same
tag-id. In such case you should use ``GET /tags/<ngo>/<tag-id>/device``
to unequivocally get the correct device (feature to develop).

Tags and migrations
*******************
Tags travel with the devices they are linked when migrating them. Future
implementations can parameterize this.

Photochromic tags
*****************
The photochromic Reversible Tag helps the end-user to identify a
legitimate device that has correctly refurbished by an eReuse.org
authorized refurbisher, without the hassle to read the QR code.

Only eReuse.org authorized organizations can use the Photochromic tags.

Use-case with eTags
*******************
We explain the use-case of tagging a device with an :ref:`tags:eTags`,
going through the manufacturing of the tags, their distribution and
the final linkage between tag and computer.

For this use-case we suppose we want 100 eTags.

Actors
======

- Tag provider: organization that orders and manages the eTags; it is
  certified by eReuse.org thus having permission to order the tags.
- NFC Tag manufacturer.
- Photochromic tag manufacturer.
- User: organization that uses the tags.

Requirements
============

- At least one eReuse.org Devicehub. One Devicehub can contain several
  organizations and inventories, or organizations can have their own
  copy of Devicehub. Devicehub work distributely over the Internet.
- One `eReuse.org Tag <https://github.com/ereuse/tag>`_ running in a
  server over the Internet by the *tag provider*.

Use case
========

1. The *tag provider* enters into the server containing the
   *eReuse.org Tag* software and executes the command
   ``etag create-tags 100 --csv file.csv``, which creates 100
   tags in the database and saves their URLs into a spreadsheet CSV file
   called *file.csv*.
2. The *tag provider* sends the CSV file to the *NFC tag manufacturer*
   and orders the 100 tags.
3. The *NFC tag manufacturer* creates those tags (NFC plus QR code)
   and updates the CSV file with the NFC ID of each tag, so each row
   of the CSV file contains the URL sent by the *tag provider* and
   the ID of the NFC tag created by the *NFC tag manufacturer*.
4. The *Tag provider* updates *eReuse.org Tag* with the ID of the
   NFC by executing ``etag update-tags file.csv`` where *file.csv* is the
   file sent by the *NFC tag manufacturer*.
5. The *Tag provider* orders 100 photochromic tags to the *Photochromic
   tag manufacturer*. Note that these tags don't require any special
   treatment.
6. The *Photochromic tag manufacturer* sends back 100 tags.
7. The *Tag provider* distributes the eTags (NFC and photochromic) to
   several organizations, *users*, both physically by sending them and
   virtually by executing ``etag set-tags http://some-devicehub.com
   0 100``; this marks the tags in *eReuse.org Tag*
   as *sent to some-devicehub.com* and creates the tags in that
   Devicehub.
8. The *user* receives the tags, sticks them in their devices, and scans
   the NFC or QR codes:

   1. By using the `eReuse.org Android App <https://github.com/eReuse/eReuseAndroidApp>`_
      the user can scan the QR code or the NFC of the eTag.
   2. If the *user* is processing devices with the
      `eReuse.org Workbench <https://github.com/ereuse/workbench>`_, Workbench
      automatically attaches hardware information like serial numbers,
      otherwise the *user* can add that information through the app.
   3. These softwares communicate with the Devicehub of the user and
      command the Devicehub to link the device with the tag.
   4. The Devicehub of the user links the tag.
   5. The Devicehub creates or updates a virtual entity in Everythng
      containing the device and the tag.
   6. If Devicehub or Everythng detect that the tag was linked they won't
      allow this operation. Devicehub can only detect if the app is linked
      by looking at its internal database. Everythng, as it contains all
      device and tag information, validates that the tag is not linked
      elsewhere.
