Using the API
#############

Devicehub is a REST API on the web that partially extends Schema.org's
ontology and it is formatted in JSON.

The main resource are devices. However, you do not perform operations
directly against them (there is no ``POST /device``),
as you use an Action / Event to do so (you only ``GET /devices``).
For example, to upload information of devices with tests, erasures, etcetera, use
the action/event ``POST /snapshot`` (:ref:`devices-snapshot`).

Login
*****
To use the API, you need first to log in with an existing account from the DeviceHub.
Perform ``POST /users/login/`` with the email and password fields filled::

  POST /users/login/
  Content-Type: application/json
  Accept: application/json
  {
    "email": "user@dhub.com",
    "password: "1234"
  }

Upon success, you are answered with the account object, containing a Token field::

  {
    "id": "...",
    "token: "A base 64 codified token",
    "type": "User",
    "inventories": [{"type": "Inventory", id: "db1", ...}, ...],
    ...
  }

From this moment, any other following operation against
the API requires the following HTTP Header:
``Authorization: Basic token``. This is, the word **Basic**
followed with a **space** and then the **token**,
obtained from the account object above, **exactly as it is**.

.. _authenticate-requests:


Authenticate requests
---------------------
To explain how to operate with resources like events or devices, we
use one as an example: obtaining devices. The template of
a request is::

   GET <inventory>/devices/
   Accept: application/json
   Authorization: Basic <token>

And an example is::

    GET acme/devices/
    Accept: application/json
    Authorization: Basic myTokenInBase64

Let's go through the variables:

- ``<inventory>`` is the name of the inventory where you operate.
  You get this value from the ``User`` object returned from the login.
  The ``inventories`` field contains a set of databases the account
  can operate with, being the first inventory the default one.
- ``<token>`` is the token of the account.

See :ref:`devices:devices` for more information on how to query
devices.
