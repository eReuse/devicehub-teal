Devicehub
#########
Devicehub is a distributed IT Asset Management System focused in reusing
devices, created under the project
`eReuse.org <https://www.ereuse.org>`__.

This README explains how to install and use Devicehub.
`The documentation <http://devicehub.ereuse.org>`_ explains the concepts
and the API.

Devicehub is built with `Teal <https://github.com/ereuse/teal>`__ and
`Flask <http://flask.pocoo.org>`__.

Installing
**********
The requirements are:

-  Python 3.7.3 or higher. In debian 10 is ``# apt install python3``.
-  `PostgreSQL 11 or higher <https://www.postgresql.org/download/>`__.
-  Weasyprint
   `dependencies <http://weasyprint.readthedocs.io/en/stable/install.html>`__.

Install Devicehub with *pip*:
``pip3 install -U -r requirements.txt -e .``.

Running
*******
Create a PostgreSQL database called *devicehub* by running
`create-db <examples/create-db.sh>`__:

-  In Linux, execute the following two commands (adapt them to your distro):

   1. ``sudo su - postgres``.
   2. ``bash examples/create-db.sh devicehub dhub``, and password
      ``ereuse``.

-  In MacOS: ``bash examples/create-db.sh devicehub dhub``, and password
   ``ereuse``.

Using the `dh` tool for set up with one or multiple inventories.
Create the tables in the database by executing:

.. code:: bash

   $  export dhi=dbtest;  dh inv add --common --name dbtest

Finally, run the app:

.. code:: bash

   $ export dhi=dbtest;dh run --debugger

The error ‘bdist_wheel’ can happen when you work with a *virtual environment*.
To fix it, install in the *virtual environment* wheel
package. ``pip3 install wheel``

Multiple instances
------------------
Devicehub can run as a single inventory or with multiple inventories,
each inventory being an instance of the ``devicehub``. To add a new inventory 
execute:

.. code:: bash

   $ export dhi=dbtest;  dh inv add --name dbtest

Note: The ``dh`` command is like ``flask``, but
it allows you to create and delete instances, and interface to them
directly.


Testing
*******
1. ``git clone`` this project.
2. Create a database for testing executing ``create-db.sh`` like the
   normal installation but changing the first parameter from
   ``devicehub`` to ``dh_test``: ``create-db.sh dh_test dhub`` and
   password ``ereuse``.
3. Execute at the root folder of the project ``python3 setup.py test``.

Generating the docs
*******************

1. ``git clone`` this project.
2. Install plantuml. In Debian 9 is ``# apt install plantuml``.
3. Execute ``pip3 install -e .[docs]`` in the project root folder.
4. Go to ``<project root folder>/docs`` and execute ``make html``.
   Repeat this step to generate new docs.

To auto-generate the docs do ``pip3 install -e .[docs-auto]``, then
execute, in the root folder of the project
``sphinx-autobuild docs docs/_build/html``.
