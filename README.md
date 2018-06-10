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

## Installation
The requirements are:

- Python 3.5 or higher.
- PostgreSQL 9.6 or higher.

Install Devicehub with *pip*: `pip3 install ereuse-devicehub`.

## Running
To use it create a python file with the following and call it `app.py`:
```python
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.config import DevicehubConfig
class MyConfig(DevicehubConfig):
    ORGANIZATION_NAME = 'My org'
    ORGANIZATION_TAX_ID = 'foo-bar'


app = Devicehub(MyConfig())
```
Crate a PostgreSQL database:
```bash
$ createdb dh-db1
```

And then execute, in the same directory where `app.py` is:
```bash
$ flask run
```

See the [Flask quickstart](http://flask.pocoo.org/docs/1.0/quickstart/)
for more info.