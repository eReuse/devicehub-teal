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

- Python 3.5.3 or higher. In debian 9 is `# apt install python3-pip`.
- PostgreSQL 9.6 or higher. In debian 9 is `# apt install postgresql`
- passlib. In debian 9 is `# apt install python3-passlib`.

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
sudo su - postgres  # Change to Postgres main user
postgres $ createdb devicehub  # Create main database
postgres $ psql devicehub  # Access to the database
postgres $ CREATE USER dhub WITH PASSWORD 'ereuse';  # Create user devicehub uses to access db
postgres $ GRANT ALL PRIVILEGES ON DATABASE devicehub TO dhub;  # Give access to the db
postgres $ \q
exit
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

The error `flask: command not found` can happen when you are not in a 
*virtual environment*. Try executing then `python3 -m flask`. 

See the [Flask quickstart](http://flask.pocoo.org/docs/1.0/quickstart/)
for more info.

## Administrating
Devicehub has many commands that allows you to administrate it. You
can, for example, create a dummy database of devices with ``flask dummy``
or create users with ``flask create-user``. See all the
available commands by just executing ``flask`` and get more information
per command by executing ``flask command --help``.

## Understand the software
See the [docs](docs/index.rst) to understand how the software works and 
the design principles.

### Use the API
Checkout [Swagger](https://app.swaggerhub.com/apis/ereuse/devicehub/0.2)
to see the schemas and endpoints (we are working  in making it 
interactive).

Use postman as an example of how to use the API.

[![Run in Postman](https://run.pstmn.io/button.svg)](https://documenter.getpostman.com/view/254251/RWEnmFPs)
