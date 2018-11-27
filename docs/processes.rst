Processes
#########

This is a unclosed list of processes that you can do in Devicehub.
Use them as a reference.

..  toctree::
    :maxdepth: 4

    processes


Registration and refurbish
**************************

Tag provisioning
================
Please refer to :ref:`tags:Use case`.

Processing a device with Workbench
==================================
Processing a device with the `eReuse.org Workbench
<https://github.com/ereuse/workbench>`_ means creating a hardware
report of the device (including serial numbers and other metadata),
linking the device with tags, and registering it to a Devicehub.

This is the first step when dealing with a new device with
the eReuse.org tools, as it registers the device with the database,
or updates its information if the device existed before. So any
other process, unless stated contrary, requires this one to be
performed to a device before.

For generic devices, the process is as follows:

1. The user opens the eReuse.org Android App (App) and selects
   *add snapshot*.
2. The user sticks and scans the tags of the device, including the
   :ref:`tags:eTags`, manufacturer tags (like serial numbers), and
   tags provided by third-parties like donors.
3. The user manually introduces other information, like ratings,
   finally submitting the information to Devicehub.

For a computer, `This video <https://vimeo.com/250253019>`_ explains
the process, and it is as follows:

1. The user connects the computers to process to an eReuse.org Box
   running the Workbench Server software using a local network.
2. Computers boot and automatically execute the eReuse.org Workbench
   software, generating information from the computer and its components,
   erasing the data storage components, testing the machine, etc.
3. During the process, the user opens the Android App and selects
   the *Workbench* option, which connects the App to a running
   Workbench Server in the local network.
4. From now on, like in step 2. from the generic device, the user
   sticks and scans the tags from the device, specifically the
   :ref:`tags:eTags` and the ones provided by third-parties. The
   manufacturer tags are not required as such information is taken
   by the Workbench automatically.
5. Android App and Workbench embed the information into a report
   that is submitted to Devicehub.

.. _prepare:

Preparing a device for use
==========================
Users, like refurbishers, ready the devices so they are suitable
for trading. This process implies repairing, cleaning, etc.

1. The user scans the tag of the device with the Android App or searches it from the
   website and selects *actions* > :ref:`actions:ToPrepare`,
   which informs Devicehub that a device has to be prepared for trading.
2. The user prepares the device. Upon success, it performs the action
   :ref:`actions:Prepare` in the similar way that
   did in 1.
3. A prepared device might still not be ready for trading. For example,
   a seller still might want to clean a device once a trade has been
   confirmed, for example because the device gathered dust between
   the preparation and trading. To denote a final "this device is
   ready to be used or shipped", the user performs
   the action :ref:`actions:ReadyToUse` in the same way it did in 1.

If the device is broken or it breaks, the user performs the action
:ref:`actions:ToRepair` denoting that the device has to be repaired,
and :ref:`actions:Repair` upon success.

Broken devices that are not going to be fixed are set to
`Dispose a device`_.

Track a device
==============
`processing a device with workbench`_ registers into Devicehub
the required metadata from a device to identify it: a digital
passport for the device (information submitted in a Devicehub),
plus a physical passport (a tag that links the device with the digital
passport). If the physical passport is an :ref:`tags:eTags` then
it is unforgeable.

The rest of the traceability is based in keeping track of the events
occurring on the device, for example when it changes location or
it is traded. eReuse.org allows recording these actions, providing
mechanisms to ease them or ensure them. Please refer to the specific
use cases for more information.

.. _share:

Share device information
========================
Users can generate public links to share with external users, like
retailers or donors, so they can see a subset of the metadata. Thanks
to this, external users can audit the devices (donors, consumers), take
confident and faster decisions when requesting devices (retailers,
consumers).

This information includes hardware information, device rates,
device price (both guessed and manually set), and a public part of
the traceability log.

To share devices:

1. The user scan the tags of the devices it wants to share with the
   Android App or searches the devices through the website.
2. The user select *generate sharing links*, which gives it a list of
   public links of the devices.
3. Users send those links to their contacts using their preferred
   method, like e-mail.
4. External users visit those links in order to see a web page
   containing the public information of the device.

Public information of a device is always accessible when an user
scans the QR of the tag through its smartphone, as the QR contains
a public link of the device. This way people in physical contact with the
device, like consumers, can always check information about the device.


.. _public-webpage:

The public webpage
------------------
The public webpage of a device includes:

   - A description of the device, including specifications,
     public identifiers, and associated tags.
   - Instructions in how to challenge the Photochromic tag of the
     device for `checking device authenticity`_.
   - Traceability log of the device.
   - :ref:`The public custody chain for present devices <public-custody>`.
   - Certificates like erasures.

Checking device authenticity
============================
Any user can check the authenticity of a device registered in a
Devicehub, even if the user is not registered, like a customer.

If the device has an :ref:`tags:eTags` or a regular tag generated by
a Devicehub (stuck on the `Processing a device with Workbench`_),
the process is as follows:

1. The user scans the QR code with a smartphone using a generic QR
   code scanner.
2. The scanner opens the browser and takes the user to
   `the public webpage`_ containing public information of the
   device, like identifiers and instructions in how to challenge the
   photochromic tag.
3. The user tests the photochromic tag by touching the flash bulb of
   the smartphone with the tag for, at least, 6 seconds, checking
   that the tag changes color temporarily.

Other ways of checking device authenticity are:

- Scanning the QR code stuck and comparing the serial numbers of the
  device with the ones of the public webpage.
- Directly applying the photochromic challenge.

Workbench and Devicehub detect changes in computer components. Certain
scenarios where the computer passed by untrusted users require
ensuring that no component has been taken or replaced.
A deeper verification process is re-processing the computer with
Workbench, generating a new report that updates the information of
the computer in the Devicehub, ultimately showing the differences
in removed and added components.

Finally, the eReuse.org team is developing, using the platform Evrythng,
a global record of devices, which takes non-private IDs of the devices
of participating Devicehubs and records the most important life
events of the devices. This database is publicly available, so
users can search on it an ID of a device, for example the S/N or the one
written in a tag, like an :ref:`tags:eTags`, and know which Devicehub is
registered in, ultimately accessing the public information of the device.

Recover a lost device
=====================
Users can recover a lost device found in a waste dump by following the
process of `checking device authenticity`_.

A Devicehub participating in the global record of devices (explained
in `checking device authenticity`_) automatically uploads public
device information into Evrythng. If the device was previously
registered in another Devicehub and there is no record of trading
between Devicehubs, Evrythng warns both systems. Note that this
functionality is in development.

Rating a device
===============
Rating a device is the act of grading the appearance, performance,
and functionality of a device. This results in a :ref:`actions:Rate`
action, which includes a guessed **price** for the device.

There are two ways of rating a device:

1. When processing a computer with Workbench and the Android App.

   1. While Workbench is processing the machine, the user
      links the tag with the computer. In this process, as it requires the
      user to scan the tag with the App, the app allows the user to introduce
      more information, including the appearance and functionality.
   2. The App embeds the rate with the device report generated by the
      Workbench.
   3. The Workbench uploads the report to Devicehub.
2. Anytime with the Android App or website.

   - The user scans the tag of the device with the Android App.
     After scanning it, the App allows the user to rate the
     appearance and functionality.
   - Through the website, the user searches the device and then
     selects to perform a new :ref:`actions:ManualRate`, rating
     the appearance and functionality.

In any case, when Devicehub receives the ratings, it computes a final
global :ref:`actions:Rate`, embedding a guessed price for the device.

Refer to :ref:`actions:Rate` for technical details.

.. _storing:

Storing devices
===============
Devices are stored in places like warehouses.

:ref:`lots:`, :ref:`actions:Locate`, :ref:`actions:Receive`,
and :ref:`actions:Live`, actions help locating devices,
from a global scale to inside places.

The :ref:`actions:Locate`, :ref:`actions:Receive`,
and :ref:`actions:Live` embed approximated city or province level
information, and the user can write a location, name, or address
in Locate and Receive. This location can be as detailed as required,
like shelves in a building. Users can create actions by scanning
a tag with the App or searching a device through the website,
and then selecting *create an action*.

Lots are more versatile than actions, and they do not pollute the
traceability log, which is unneeded when placing devices in temporal
places like warehouses. Lots act like folders in an Operative System,
so the user is free to choose what each lot represents —for example
physical locations:

- Lot company ACME

  - Lot Warehouse 1 of ACME

    - Lot Zone A

      - Computer 1
      - Monitor 2

To create a lot the user uses the webiste or App, selecting *create lot*
and giving it a name.

To place devices inside a lot through the website, the user selects
the devices, it presses *add to lot*, and writes the name of the lot.
To place them through the App, the user scans the tags of the devices,
it presses *add to lot*, and writes the name of the lot.

To look for devices the user reduces the area to look for them by
checking to which lot the device is. This is done through the website
or App by searching the device and checking to which lots is inside,
or searching the lot and checking which devices are inside. Once the
user is in the place, it picks up the correct device by reading
its tag.

Erasing data and obtaining a certificate
========================================

When `Processing a device with Workbench`_ user can order Workbench
to erase the data stroage units. In the configuration users parametrize
the erasure to follow their desired erasure standard (involving
customizing erasure steps).

Once the Workbench uploads the report to a Devicehub, the user gets
the erasure certificate of the (data storage units of the) computer.

A logged-in user with access to the device can scan the tag with
the App or search the device through the web app and select
*certificates*, then *erasure certificate*, to view an on-line
version of the certificate and download a PDF.

An external user can access `The public webpage`_ of the device
to download the erasure certificate.

Please refer to :ref:`actions:Erase` for detailed information about
how erasures work and which information they take.

.. _delivery:

Delivery
========
:ref:`actions:Receive` is the act of physically taking delivery of a
device. When an user performs a Receive, it means that another user took
the device physically, confirming reception.

To perform this action the user scans the tag of the devices with the App,
or search it through the website, and selects *actions* > *Receive*,
filling information about the receiver and delivery.

An exemplifying case is delivering a device from the warehouse to
a customer through a transporter:

1. Warehouse employees look in the website devices that are sold,
   donated, rented (:ref:`actions:Trade`) that are still in
   the warehouse and ready to be used.
2. They :ref:`store devices <storing>` in the warehouse.
3. Once the devices are located the employees give them to the
   transporter. To acknowledge this to the system, they scan the
   tags of those devices with the App and perform the action
   :ref:`actions:Receive`, stating that the transporter received the
   devices.
4. The transporter takes the devices to the customer, performing the
   same :ref:`actions:Receive` again, this time stating that the
   customer received the devices.

The last :ref:`actions:Receive` of a delivery, the one referring
to the final customer, can :ref:`activate the warranty <warranty>`.

Value (price) devices
=====================
Devicehub guesses automatically a price after each new rate, explained
in `Rating a device`_, and manually by performing the action
:ref:`actions:Price`. By doing manually it, the user can set any
price.

To perform a manual price the user scans the tags of the devices
with the App, or searches them through the website, and selects
*actions* > *price*.

The user has still a chance to set the final trading price when
performing :ref:`actions:Trade`. If the user does not set any price,
and the trade is not a :ref:`actions:Donation` or similar, Devicehub
assumes that the last known price is the one which the device is
sold.

Refer to :ref:`actions:Price` to know the technical details in how
Devicehub guesses the price.

Manage sale with buyer (reserve, outgoing lots, sell, receive)
==============================================================
We exemplify the use of lots and actions to manage sales with
a buyer.

1. The first step on sales is for a seller to showcase the devices
   to potential customers by :ref:`sharing them <share>`.
2. A customer inquires about the devices, for example through e-mail.
3. This can imply a reservation process.
   In such case, the seller can perform the action :ref:`actions:Reserve`,
   which reserves the selected devices for the customer.
   To perform that action, the user scan the tags of the devices
   with the App or search them through the website, select them,
   and click *actions* > *Reserve*.
2. Reservations can be cancelled but not modified nor deleted. To cancel a
   reservation the user uses the App or the web to select the devices,
   and look for their reservation to cancel it.
3. A reservation is fulfilled once the customer buys, gets through, or rents
   a device; for example by an e-commerce or through a confirmation e-mail.
   To perform any of those actions in Devicehub,
   a seller selects the devices and clicks
   *actions* > *Sell*, *Donate*, or *Rent*. It can perform those actions
   over devices that are not reserved, or mix reserved devices with
   non-reserved devices. Refer to :ref:`actions:Trade`.
4. Lots help sellers in keeping an order in sales. A good ordering is
   creating a lot called ``Sales``, and then, inside that lot,
   a lot for each sales, and/or a lot for each customer.
5. The seller gets confirmation from the warehouse or refurbisher
   that the devices have :ref:`been prepared for use <prepare>`.
6. Devices are :ref:`delivered <delivery>` to the customer.

Verify refurbishment of a device through the tag
================================================

.. todo called Verify refurbishment of end-user's device

Devicehub and eReuse.org allows usage of the :ref:`tags:Photochromic tags`
to visually assist users, at-a-glance, in verifying correctly non-fraudulent
refurbishing of a device.

Users like refurbishers stick the tags on the devices.

On the end-user side:

1. The end-user wants to verify refurbishment from a device of a retailer.
2. The End-user sees a QR in a tag, like the the :ref:`tags:eTags`,
   which scans with its smartphone's QR reader app, taking the
   user to the :ref:`Share device information <public-webpage>`.
3. The public web page contains, along information about the device,
   instructions on how to check the validity of the Photochromic tag
   — consisting on illuminating the tag with the smartphone's lantern
   during a minimum of 6 seconds.

Delivery or pickup from buyer after use
=======================================
After customer usage devices can be picked-up so they are prepared
for re-use or recycle.

.. todo what happens if the device is from another inventory?

Once the customer agrees for the devices to be taken, a transporter
or the same customer takes the device to the warehouse, and an
employee performs a :ref:`actions:Receive` to state that a device has been
physically received, and a :ref:`actions:Trade` to state the change of
property. These actions can be performed by scanning the tag with
the App or by manually searching the device through the website.

.. _dispose:

Dispose a device
================
Users can manage the disposal of devices in Devicehub. A disposal
in Devicehub means two things: 1) trading devices to a company that
manages its 2) final destruction or recovery.

The first case is managed by the actions
:ref:`actions:ToDisposeProduct, DisposeProduct`:

1. An user marks a device to be disposed by scanning the tag of the
   device or searching it through the website and selecting
   *actions* > *ToDisposeProduct*.
2. When the organization in charge of the disposition takes the device
   the user performs *actions* > *DisposeProduct*.

.. todo when takes the devices (receive?) or when agreed (trade)?

The latter case is managed by the actions
:ref:`actions:DisposeWaste, Recover`. The user performs the action
*DisposeWaste* when the product has been destroyed and put into waste,
and *Recover* when the product has been recycled.

Retail and distribution
***********************

Make devices available for sale to final users
==============================================
Once the devices are registered in the Devicehub, users can share
the devices to potential customers. Please refer to
:ref:`share devices information <share>`.

Manage purchase of devices with refurbisher / ITAD
==================================================
Please refer to `Manage sale with buyer (reserve, outgoing lots, sell, receive)`_.

Distribution of devices
=======================
Please refer to `Delivery or pickup from buyer after use`_.

Transport between service providers and buyers
==============================================
Please refer to `Delivery or pickup from buyer after use`_.

Estimate selling price
======================
Please refer to `Value (price) devices`_.

Manage donations and interactions with donors
=============================================
(Nope)

Post-sale channel support
*************************

Customer service for hardware issues
====================================
Devicehub allows introducing contact information in the
:ref:`public webpage <public-webpage>` of the device,
including an e-mail and phone number.

This information is based on the default organization, which an
administrator sets when installing Devicehub.

.. todo program this

.. _warranty:

Provide hardware warranty
=========================
Devicehub helps in recording the day the warranty is activated by
saving in the traceability log the `Delivery`_ of the device to the final
user. Specifically, an user can check the last :ref:`actions:Receive`
(step 4. of `Delivery`_) to be the one that activates the warranty.

Recyclers
*********

Get the certification for recycling
===================================
Recyclers can obtain a certificate after performing a
:ref:`Dispose a device <dispose>` to devices.

To obtain the certificate, the user scans the tags of the devices with
the Android App or searches them through the web, and then selects
*certificate* > *recycling*.

.. todo defined but not programmed

Device reuse management
***********************

Pick-up at donor
================
Please see `Manage donations and interactions with donors`_.

Transfer donations to refurbishers
==================================
(Nope)

Get internal custody chain report for donation
==============================================
Users can obtain the internal custody chain report for donation
as an comma separated value spreadsheet.

To obtain the document, the user scans the tags of the devices with
the Android App or searches them through the web, and then selects
*certificate* > *Internal custody chain report for donation*.

Users can see part of this information too by selecting *Actions*
after selecting a device, resulting in a web view of the traceability
log of the device.

.. todo defined but not programmed

.. _public-custody:

View public custody chain for present devices
=============================================
The public custody chain of a device is part of the public information
of the device that users can :ref:`share device information <share>`.
