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

# from flask_wtf.csrf import CSRFProtect


# from werkzeug.middleware.profiler import ProfilerMiddleware


SENTRY_DSN = config('SENTRY_DSN', None)
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            FlaskIntegration(),
        ],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
    )


app = Devicehub(inventory=DevicehubConfig.DB_SCHEMA)
app.register_blueprint(core)
app.register_blueprint(devices)
app.register_blueprint(labels)
app.register_blueprint(api)
app.register_blueprint(workbench)

# configure & enable CSRF of Flask-WTF
# NOTE: enable by blueprint to exclude API views
# TODO(@slamora: enable by default & exclude API views when decouple of Teal is completed
# csrf = CSRFProtect(app)
# csrf.protect(core)
# csrf.protect(devices)
# app.config["SQLALCHEMY_RECORD_QUERIES"] = True
# app.config['PROFILE'] = True
# app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
# app.run(debug=True)
