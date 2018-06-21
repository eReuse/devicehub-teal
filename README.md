# Devicehub

Devicehub is an IT Asset Management System focused in reusing devices,
created under the project [eReuse.org](https://www.ereuse.org).

Our main objectives are:

- To offer a common IT Asset Management for donors, receivers and IT 
  professionals so they can manage devices and exchange them.
  This is, reusing –and ultimately recycling.
- To automatically recollect, analyse, process and share 
  (controlling privacy) metadata about devices with other tools of the
  eReuse ecosystem to guarantee traceability, and to provide inputs for 
  the indicators which measure circularity.
- To highly integrate with existing IT Asset Management Systems.
- To be decentralized.

Devicehub is built with [Teal](https://github.com/bustawin/teal) and
[Flask](http://flask.pocoo.org).

## Installing
The requirements are:

- Python 3.5 or higher.
- PostgreSQL 9.6 or higher.
- passlib. In debian is ``apt install python3-passlib``.

Install Devicehub with *pip*: `pip3 install ereuse-devicehub -U --pre`.

## Running
Create a python file with the following and call it `app.py`:
```python
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.config import DevicehubConfig
class MyConfig(DevicehubConfig):
    ORGANIZATION_NAME = 'My org'
    ORGANIZATION_TAX_ID = 'foo-bar'


app = Devicehub(MyConfig())
```
Create a PostgreSQL database called *devicehub*:

```bash
# su - postgres
postgres $ createdb devicehub
postgres $ psql devicehub
postgres $ GRANT ALL PRIVILEGES ON DATABASE devicehub TO dhub;
postgres $ \q
```

Create the tables in the database by executing in the same directory 
where `app.py` is:

```bash
$ flask init-db
```

Finally, run the app:

```bash
$ flask run
```

See the [Flask quickstart](http://flask.pocoo.org/docs/1.0/quickstart/)
for more info.

## Administrating
Devicehub has many commands that allows you to administrate it. You
can, for example, create a dummy database of devices with ``flask dummy``
or create users with ``flask create-user``. See all the
available commands by just executing ``flask`` and get more information
per command by executing ``flask command --help``.