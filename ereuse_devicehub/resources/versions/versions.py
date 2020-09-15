import flask
import json
import teal.marshmallow
import ereuse_utils

from typing import Callable, Iterable, Tuple
from flask import make_response, g
from teal.resource import Resource, View


class VersionView(View):
    def get(self, *args, **kwargs):
        """Get version."""
        v = "{}".format(ereuse_utils.version('ereuse-devicehub'))
        return json.dumps({'devicehub': v})


class VersionDef(Resource):
    __type__ = 'Version'
    SCHEMA = None
    VIEW = None  # We do not want to create default / documents endpoint
    AUTH = False

    def __init__(self, app,
                 import_name=__name__,
                 static_folder='static',
                 static_url_path=None,
                 template_folder='templates',
                 url_prefix=None,
                 subdomain=None,
                 url_defaults=None,
                 root_path=None,
                 cli_commands: Iterable[Tuple[Callable, str or None]] = tuple()):
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)

        d = {'devicehub': '0.1.0a'}
        get = {'GET'}

        version_view = VersionView.as_view('stockDocumentView', definition=self)
        self.add_url_rule('/', defaults=d, view_func=version_view, methods=get)
