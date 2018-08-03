Use-case with eTags
###################
We explain the use-case of tagging a device with an :ref:`tags:eTags`,
going through the manufacturing of the tags, their distribution and
the final linkage between tag and computer.

For this use-case we suppose we want 100 eTags.

Actors
******

- Tag provider: organization that orders and manages the eTags; it is
  certified by eReuse.org thus having permission to order the tags.
- NFC Tag manufacturer.
- Photochromic tag manufacturer.
- User: organization that uses the tags.

Requirements
************

- At least one eReuse.org Devicehub. One Devicehub can contain several
  organizations and inventories, or organizations can have their own
  copy of Devicehub. Devicehub work distributely over the Internet.
- One `eReuse.org Tag <https://github.com/ereuse/tag>`_ running in a
  server over the Internet by the *tag provider*.

Use case
********

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
   2. If the *user* is processing devices with the `eReuse.org
      Workbench <https://github.com/ereuse/workbench>`_, Workbench
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
