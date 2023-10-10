"""
Example app with minimal configuration.

Use this as a starting point.
"""

from decouple import config

from ereuse_devicehub.api.views import api
from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.inventory.views import devices
from ereuse_devicehub.labels.views import labels
from ereuse_devicehub.views import core
from ereuse_devicehub.workbench.views import workbench
from ereuse_devicehub.modules.did.views import did
from ereuse_devicehub.modules.dpp.views import dpp
from ereuse_devicehub.modules.oidc.views import oidc
from ereuse_devicehub.modules.oidc.oauth2 import config_oauth

app = Devicehub(inventory=DevicehubConfig.DB_SCHEMA)
app.register_blueprint(core)
app.register_blueprint(devices)
app.register_blueprint(labels)
app.register_blueprint(api)
app.register_blueprint(workbench)
app.register_blueprint(did)
app.register_blueprint(dpp)
app.register_blueprint(oidc)


config_oauth(app)

