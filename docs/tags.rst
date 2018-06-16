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
an ID and an tag provider. Future Devicehub versions can allow
parametrizing an ID generator.

Note that these virtual tags don't have to forcefully be printed or
have a physical representation (this is not imposed at system level).

The eReuse.org tags (eTag)
**************************
We recognize a special type of tag, the **eReuse.org tags (eTag)**.
These are tags defined by eReuse.org and that can be issued only
by tag providers that comply with the eReuse.org requisites.

The eTags are designed to empower device exchange between
organizations and identification efficiency. They are built with durable
plastic and have a QR code, NFC chip and a written ID.

These tags live in separate databases from Devicehubs, empowered by
the `eReuse.org Tag <https://github.com/ereuse/tag>`_. By using this
software, eReuse.org certified tag providers can create and manage
the tags, and send them to Devicehubs of their choice.

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
to inequivocally get the correct device (to develop).

Tags and migrations
*******************
Tags travel with the devices they are linked when migrating them. Future
implementations can parameterize this.

http://t.devicetag.io/TG-1234567890