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

Track a device
==============

Recover a lost device
=====================

Rating a device
===============
Rating a device is the act of grading the appearance, performance,
and functionality of a device. This results in a :ref:`actions:Rate`
action, which includes a guessed **price** for the device.

There are two ways of rating a device:

1. When processing a computer with Workbench and the Android App.
2. Anytime with the Android App or website.

When processing a computer with the Workbench, once the user scans the
tag, it is showed with a screen where it can rate the appearance and
functionality. Once done, this data is added to the report of the
Workbench, which includes the automatic performance grade, and it is
uploaded to Devicehub, computing the :ref:`actions:Rate` with the
final total rate and guessed price.

.. todo this is not done yet

The second way is opening the App, scan the tag of the device, and
then select *rate* to write the appearance and functionality. The
same process can be done through the website by searching the device.
Note that with this process there is no way of introducing the
performance, as it is computed by Workbench, meaning that Devicehub
takes the last known performance value to compute a new Rate.

Refer to :ref:`actions:Rate` for technical details.

Storing devices
===============
Devices are stored in places like warehouses.

:ref:`lots:`, :ref:`actions:Locate`, :ref:`actions:Receive`,
and :ref:`actions:Live`, actions help locating devices,
from a global scale to inside places.

The :ref:`actions:Locate`, :ref:`actions:Receive`,
and :ref:`actions:Live`; embed approximated city or province level
information, and the user can write a location, name, or address
in Locate and Receive. This location can be as detailed as required,
like shelves in a building. Users can create actions by scanning
a tag with the App or searching a device through the website,
and then selecting *create an action*.

Lots are more versatile than actions, and they do not pollute the
traceability log, which is not needed when placing devices in temporal
places like warehouses. Lots act like folders in an Operative System,
so the user is free to choose what each lot represents, like representing
physical locations. For example:

- Lot company ACME

  - Lot Warehouse 1 of ACME

    - Lot Zone A

      - Computer 1
      - Monitor 2

Users create lots through the website or App, selecting *create lot*,
and then can place devices as they were files and folders. With the
App users can select multiple devices and move all of them to a lot.

To look for devices users reduce the area to look for them by
checking to which lot the device is. And then, they visually check
the identifier printed in the tags of devices in that place
to find the ones they are looking for.

Erasing data and obtaining a certificate
========================================

.. todo add a reference that explains how Workbench works in general

Workbench erases data storage units, once the user configured Workbench
to do so. In the configuration users parameterize the erasure to
follow their desired erasure standard (which involves selecting
erasure steps, data written or verification, for example).

Once the Workbench uploads the report to a Devicehub, users can get
the erasure certificate of the (data storage units of the) computer.

An external user, like a client, if scans the tag with a smartphone,
can see an on-line version of the certificate with its smartphone
web browser.

A logged-in user with access to the device, can scan the tag with
the App or search the device through the web app and select
*certificates*, then *erasure certificate*, to view an on-line
version of the certificate and download a PDF.

Please refer to :ref:`actions:Erase` for detailed information about
how erasures work and which information they take.

Delivery
========
:ref:`actions:Receive` is the act of physically taking delivery of a
device. When an user performs a Receive, it means that another user took
the device physically, confirming reception.

To perform this action scan the tag of the devices with the App,
or search it through the website, and select *actions* > *Receive*,
filling information about the receiver and delivery.

An exemplifying case is delivering a device from the warehouse to
a customer through a transporter:

1. Warehouse employees look in the website devices that are
   :ref:`actions:Trade` (sold, donated, rented) that are still in
   the warehouse and ready to be used.
2. They look for them in the warehouse. Refer to :ref:`Storing devices`
   for more details.
3. Once the devices are located the employees give them to the
   transporter. To acknowledge this to the system, they scan the
   tags of those devices with the App and perform the action
   :ref:`actions:Receive`, stating that the transporter received the
   devices.
4. The transporter takes the devices to the customer, performing the
   same :ref:`actions:Receive` again, this time stating that the
   customer received the devices.

Value (price) devices
=====================
Devicehub guesses automatically a price after each new rate, explained
in :ref:`Rating a device`, and manually by performing the action
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

Share device information
========================

.. todo explain too lot sharing to users?

Users can generate public links to share with external users, like
retailers or donors, so they can see a subset of the metadata. Thanks
to this, external users can audit the devices (donors, consumers), take
confident and faster decisions when requesting devices (retailers,
consumers).

This information includes hardware information, device rates,
device price (both guessed and manually set), and a public part of
the traceability log.

To share devices:

1. Users scan their tags with the Android App or searches them through
   the website.
2. They select *generate sharing links*, which gives them a list of
   public links of the devices.
3. Users send those links to their contacts using their preferred
   method, like e-mail.
4. External users visit those links in order to see a web page
   containing the public information of the device.

Public information of a device is always accessible when an user
scans the QR of the tag through its smartphone, as the QR contains
a public link of the device. This ways people in contact with the
device, like consumers, can always check information about the device.

Manage sale with buyer (reserve, outgoing lots, sell, receive)
==============================================================
We exemplify the use of lots and actions to manage sales with
a buyer.


1. The first step on sales is for a seller to showcase the devices
   to potential customers by :ref:`sharing them <share device information>`.
2. A customer inquires about the devices, for example through e-mail.
3. This can imply a reservation process.
   In such case, the seller can perform the action :ref:`actions:Reserve`,
   which reserves the selected devices for the customer.
   To perform that action, users scan the tags of the devices
   with the App or search them through the website, select them,
   and click *actions* > *Reserve*.
2. Reservations can be cancelled but not modified, as they are saved
   in the private traceability log of the devices. To cancel a
   reservation users use the App or the web to select the devices,
   and look for their reservation to cancel it. Note that reservations
   are never deleted, but marked as cancelled.
3. A reservation is fulfilled once the customer buys, gets through, or rents
   a device; for example by an e-commerce or through a confirmation e-mail.
   To perform any of those actions, sellers select the devices and click
   *actions* > *Sell*, *Donate*, or *Rent*. They can perform those actions
   over devices that are not reserved, or mix reserved devices with
   non-reserved devices. Refer to :ref:`actions:Trade`
   to know more about selling, donating, and renting.
4. Lots help sellers in keeping an order in sales. A good ordering is
   creating a lot called ``Sales``, and then, inside that lot,
   a lot for each sales, or a lot for each customer.
5. Devices have to be transported to the customer. Please refer to
   the :ref:`delivery` process for more info.


Verify refurbishment of a device through the tag
================================================

.. todo called Verify refurbishment of end-user's device

Devicehub and eReuse.org allows usage of the :ref:`tags: Photochromic tags`
to visually assist users, at-a-glance, in verifying correctly non-fraudulent
refurbishing of a device.

As the tags do not provide any technology that links them to a
specific device, they are just stuck on devices.

On the end-user side:

1. End-users buy second-hand devices from retailers.
2. End-users can apply a more throughout validation or learn about
   the life-cycle of the device by scanning the ID tag, the tag
   with a QR and/or an NFC, taking the user with the public information
   of the device (see :ref:`Share device information`.
3. The public web page contains, along information about the device,
   instructions on how to check the validity of the Photochromic tag,
   consisting on illuminating the tag with the smartphone's lantern
   during a minimum of 6 seconds.

Delivery or pickup from buyer after use
=======================================
After customer usage devices can be picked-up so they are prepared
for re-use or recycle.

.. todo what happens if the device is from another inventory?

Once the customer agrees for the devices to be taken, a transporter
or the same customer takes the device to the warehouse, and an
employee performs a :ref:`Receive` to state that a device has been
physically received, and a :ref:`Trade` to state the change of
property. These actions can be performed by scanning the tag with
the App or by manually searching the device through the website.

Retail and distribution
***********************

Make devices available for sale to final users
==============================================
Once the devices are registered in the Devicehub, users can share
the devices to potential customers. Please refer to
:ref:`share devices information`.

Manage purchase of devices with refurbisher / ITAD
==================================================

.. todo this is not available as for now

Retailers and distributors can reserve devices that are shared to them
by the refurbishers.

Una entidad puede reservar dispositivos compartidos a través de la plataforma seguiendo los siguientes pasos:

Para ello, navegue al lote eReuseCAT de la entidad que ha compartido los dispositivos.
Dentro de este lote, navegue al lote de la donación
Escoge los dispositivos que quiera reservar
Haga el evento RESERVE para reservar los dispositivos
La entidad que ha compartido los dispositivo recibirá un email. Para terminar la venta, ambos entidades gestionan la reserva.


Distribution of devices
=======================
.. es exactamente lo que ya he explicado, las únicas diferencias son
   ad-hoc de ereuse cat.


Enviar un email con los dispositivos disponibles incluyendo los IDs y los precios a las posibles entidades receptoras (compradores) o bien subir los dispositivos a una tienda online (e-commerce)
La entidad receptora escoge unos dispositivos y hace un pedido especificando los IDs de los dispositivos escogidos
Finalizar facturas y convenios con la entidad receptora
La receptora hace el pago de 100% de la factura
Hacer el evento SELL sobre los dispositivos para formalizar la venta
Preparar los dispositivos para entrega
Confirmar fecha y lugar de la entrega
Entregar dispositivos y hacer el evento RECEIVE para formalizar la entrega
Venta en colaboración con entidades comercializadoras:

​Compartir los dispositivos con las entidades especificas o con todo el circuito​
Una entidad comercializadora reserva los dispositivos​
La entidad comercializadora y receptora gestionan la reserva​

https://reutilitza-cat.gitbook.io/preguntes-frequents/como-vender-un-dispositivo
https://nextcloud.pangea.org/index.php/s/V04IMZMt4Jlxmiv/preview

Transport between service providers and buyers
==============================================
??

Estimate selling price
======================
??

Manage donations and interactions with donors
=============================================
- Como solicitar una recogida a donante
- Como hacer el convenio y reportes para el donante
- Como transferir los dispositivos del donante a uno o varios restauradores
- Como redactar la memoria

Post-sale channel support
*************************

Customer service for hardware issues
====================================
Or better said: How to handle after sales issues

Provide hardware warranty
=========================


Recyclers
*********

Get the certification for recycling
===================================
