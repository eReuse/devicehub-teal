import flask
import teal.marshmallow
import ereuse_utils

from typing import Callable, Iterable, Tuple
from flask import make_response, g
from teal.resource import Resource


class VersionDef(Resource):
    __type__ = 'Version'
    SCHEMA = None
    VIEW = None  # We do not want to create default / documents endpoint
    AUTH = False

    def __init__(self, app,
                 import_name=__name__,
                 static_url_path=None,
                 url_prefix=None,
                 subdomain=None,
                 url_defaults=None,
                 root_path=None,
                 cli_commands: Iterable[Tuple[Callable, str or None]] = tuple()):

        super().__init__(app, import_name, static_url_path,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)
        d = {'id': None}
        get = {'GET'}

        self.add_url_rule('/', defaults=d, view_func=self.view, methods=get)

    def view(self):
        #import pdb; pdb.set_trace()
        v = "{}".format(ereuse_utils.version('ereuse-devicehub'))
        return {'devicehub': v}
