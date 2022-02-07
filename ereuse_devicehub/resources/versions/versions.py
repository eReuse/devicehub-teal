import flask
import json
import requests
import teal.marshmallow

from typing import Callable, Iterable, Tuple
from urllib.parse import urlparse
from flask import make_response, g
from flask.json import jsonify
from teal.resource import Resource, View

from ereuse_devicehub.resources.inventory.model import Inventory
from ereuse_devicehub import __version__


def get_tag_version(app):
    """Get version of microservice ereuse-tag."""

    path = "/versions/version/"
    url = urlparse(Inventory.current.tag_provider.to_text())._replace(path=path)
    try:
        res = requests.get(url.geturl())
    except requests.exceptions.ConnectionError:
        app.logger.error("The microservice Tags is down!!")
        return {}

    if res.status_code == 200:
        return json.loads(res.content)
    else:
        return {}

class VersionView(View):
    def get(self, *args, **kwargs):
        """Get version of DeviceHub and ereuse-tag."""

        tag_version = get_tag_version(self.resource_def.app)
        versions = {'devicehub': __version__, "ereuse_tag": "0.0.0"}
        versions.update(tag_version)

        ret = jsonify(versions)
        ret.status_code = 200
        return ret


class VersionDef(Resource):
    __type__ = 'Version'
    SCHEMA = None
    VIEW = None  # We do not want to create default / documents endpoint
    AUTH = False

    def __init__(self, app,
                 import_name=__name__,
                 static_folder=None,
                 static_url_path=None,
                 template_folder=None,
                 url_prefix=None,
                 subdomain=None,
                 url_defaults=None,
                 root_path=None,
                 cli_commands: Iterable[Tuple[Callable, str or None]] = tuple()):
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)

        d = {'devicehub': __version__, "ereuse_tag": "0.0.0"}
        get = {'GET'}

        version_view = VersionView.as_view('VersionView', definition=self)
        self.add_url_rule('/', defaults=d, view_func=version_view, methods=get)
