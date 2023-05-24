import json
from typing import Callable, Iterable, Tuple

import flask
from boltons import urlutils
from flask import request
from flask.json import jsonify

from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.did.models import Dpp
from ereuse_devicehub.teal.resource import Resource, View


class DidView(View):
    """
    This view render one public ans static page for see the links for to do the check
    of one csv file
    """

    def get_url_path(self):
        url = urlutils.URL(request.url)
        url.normalize()
        url.path_parts = url.path_parts[:-2] + ['check', '']
        return url.to_text()

    def get(self, dpp: str):
        self.dpp = dpp
        template = 'dpp.html'
        if len(dpp.split(":")) == 2:
            result = Dpp.query.filter_by(key=dpp).one()
        else:
            result = Device.query.filter_by(chid=dpp).one()
            template = 'chid.html'

        if 'json' not in request.headers['Accept']:
            result = self.get_result(result, template)
            return flask.render_template(
                template,
                rq_url=self.get_url_path(),
                result={"dpp": dpp, "result": result},
            )

        return jsonify(self.get_result(result, template))

    def get_result(self, dpp, template):
        data = {
            'hardware': {},
            'dpp': self.dpp,
        }
        result = {'data': data}

        if template == 'dpp.html':
            data['hardware'] = json.loads(dpp.snapshot.json_hw)
            last_dpp = self.get_last_dpp(dpp)
            url_last = ''
            if last_dpp:
                url_last = 'http://did.ereuse.org/{did}'.format(did=last_dpp)
            data['url_last'] = url_last
            return result

        # if dpp is not a dpp then is a device
        device = dpp
        dpps = []
        for d in device.dpps:
            rr = {'dpp': d.key, 'hardware': json.loads(d.snapshot.json_hw)}
            dpps.append(rr)
        return {'data': dpps}

    def get_last_dpp(self, dpp):
        dpps = [
            act.dpp[0] for act in dpp.device.actions if act.t == 'Snapshot' and act.dpp
        ]
        last_dpp = ''
        for d in dpps:
            if d.key == dpp.key:
                return last_dpp
            last_dpp = d.key

        return last_dpp


class DidDef(Resource):
    __type__ = 'Did'
    SCHEMA = None
    VIEW = None  # We do not want to create default / documents endpoint
    AUTH = False

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder='static',
        static_url_path=None,
        template_folder='templates',
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )

        # view = DidView.as_view('main', definition=self, auth=app.auth)

        # if self.AUTH:
        #     view = app.auth.requires_auth(view)

        did_view = DidView.as_view('DidView', definition=self, auth=app.auth)
        self.add_url_rule(
            '/<string:dpp>', defaults={}, view_func=did_view, methods={'GET'}
        )
