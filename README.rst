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
At this stage, migration files are created manually. To apply the migrations we follow
a hybrid approach.

* When a schema is to be created in the db we create a revision file holding **all** the
necessary table definitions. For example have a look on the migration file holding the initial
declarations. There you see a full list of tables to be created. You just need to specify
the env variable **dhi**. To create a revision file execute:

.. code:: bash

   $ alembic revision -m "My initial base revision"

Then run

.. code:: bash

   $ export dhi=dbtest; dh inv add --common --name dbtest

This command will create the schemas, tables in the specified database and will stamp the
migration file you have created as the base schema for future migrations. For more info
in migration stamping please see [here](https://alembic.sqlalchemy.org/en/latest/cookbook.html)

Whenever you want to create a new schema just create a new revision with:

.. code:: bash

   $ alembic revision -m "My new base revision"

and add there **all** the tables that the new database will have. Next, you can add the
new inventory and stamp the revision as the new base.

.. code:: bash

   $ export dhi=dbtest; dh inv add --name dbtest


* When you want to alter a table, column or perform another operation on tables, create
  a revision file

.. code:: bash

   $ alembic revision -m "A table change"

Then edit the generated file with the necessary operations to perform the migration.
Apply migrations using:

.. code:: bash

   $ alembic upgrade head

* Whenever you to see a full list of migrations use

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
