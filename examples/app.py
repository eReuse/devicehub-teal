"""
Example app with minimal configuration.

Use this as a starting point.
"""
from flask_wtf.csrf import CSRFProtect

from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.inventory.views import devices
from ereuse_devicehub.views import core

app = Devicehub(inventory=DevicehubConfig.DB_SCHEMA)
app.register_blueprint(core)
app.register_blueprint(devices)

# configure & enable CSRF of Flask-WTF
# NOTE: enable by blueprint to exclude API views
# TODO(@slamora: enable by default & exclude API views when decouple of Teal is completed
csrf = CSRFProtect(app)
csrf.protect(core)
csrf.protect(devices)
