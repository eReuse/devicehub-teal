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
``pip3 install ereuse-devicehub -U --pre``.

Running
*******
Download, or copy the contents, of `this file <examples/app.py>`__, and
call the new file ``app.py``.

Create a PostgreSQL database called *devicehub* by running
`create-db <examples/create-db.sh>`__:

-  In Linux, execute the following two commands (adapt them to your distro):

   1. ``sudo su - postgres``.
   2. ``bash examples/create-db.sh devicehub dhub``, and password
      ``ereuse``.

-  In MacOS: ``bash examples/create-db.sh devicehub dhub``, and password
   ``ereuse``.

Create the tables in the database by executing in the same directory
where ``app.py`` is:

.. code:: bash

   $ flask init-db

Finally, run the app:

.. code:: bash

   $ flask run

The error ``flask: command not found`` can happen when you are not in a
*virtual environment*. Try executing then ``python3 -m flask``.

Execute ``flask`` only to know all the administration options Devicehub
offers.

See the `Flask
quickstart <http://flask.pocoo.org/docs/1.0/quickstart/>`__ for more
info.

The error ‘bdist_wheel’ can happen when you work with a *virtual environment*.
To fix it, install in the *virtual environment* wheel
package. ``pip3 install wheel``

Multiple instances
------------------
Devicehub can run as a single inventory or with multiple inventories,
each inventory being an instance of the ``devicehub``. To execute
one instance, use the ``flask`` command, to execute multiple instances
use the ``dh`` command. The ``dh`` command is like ``flask``, but
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


Migrations
**********
At this stage, migration files are created manually.
Set up the database:

.. code:: bash

   $ sudo su - postgres
   $ bash $PATH_TO_DEVIHUBTEAL/examples/create-db.sh devicehub dhub

Initialize the database:

.. code:: bash

   $ export dhi=dbtest; dh inv add --common --name dbtest

This command will create the schemas, tables in the specified database.
Then we need to stamp the initial migration.

.. code:: bash

   $ alembic stamp head


This command will set the revision **fbb7e2a0cde0_initial**  as our initial migration.
For more info in migration stamping please see https://alembic.sqlalchemy.org/en/latest/cookbook.html


Whenever a change needed eg to create a new schema, alter an existing table, column or perform any
operation on tables, create a new revision file:

.. code:: bash

   $ alembic revision -m "A table change"

This command will create a new revision file with name `<revision_id>_a_table_change`.
Edit the generated file with the necessary operations to perform the migration:

.. code:: bash

   $ alembic edit <revision_id>

Apply migrations using:

.. code:: bash

   $ alembic -x inventory=dbtest upgrade head

Then to go back to previous db version:

.. code:: bash

   $ alembic -x inventory=dbtest downgrade <revision_id>

To see a full list of migrations use

.. code:: bash

   $ alembic history


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
