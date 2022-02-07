import flask.templating

import ereuse_devicehub.resources.device.models


class Environment(flask.templating.Environment):
    """As flask's environment but with some globals set"""

    def __init__(self, app, **options):
        super().__init__(app, **options)
        self.globals[isinstance.__name__] = isinstance
        self.globals[issubclass.__name__] = issubclass
        self.globals['d'] = ereuse_devicehub.resources.device.models
