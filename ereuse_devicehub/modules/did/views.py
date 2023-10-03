import json
import logging

import flask
import requests
from ereuseapi.methods import API
from flask import Blueprint
from flask import current_app as app
from flask import g, render_template, request, session
from flask.json import jsonify
from flask.views import View

from ereuse_devicehub import __version__
from ereuse_devicehub.modules.dpp.models import Dpp, ALGORITHM
from ereuse_devicehub.resources.device.models import Device

logger = logging.getLogger(__name__)


did = Blueprint('did', __name__, url_prefix='/did', template_folder='templates')


class DidView(View):
    methods = ['GET', 'POST']
    template_name = 'anonymous.html'

    def dispatch_request(self, id_dpp):
        self.dpp = None
        self.device = None
        self.get_ids(id_dpp)

        self.context = {
            'version': __version__,
            'oidc': 'oidc' in app.blueprints.keys(),
            'user': g.user,
            'path': request.path,
            'last_dpp': None,
            'before_dpp': None,
            'rols': [],
            'rol': None,
        }
        self.get_rols()
        self.get_rol()
        self.get_device()
        self.get_last_dpp()
        self.get_before_dpp()
        self.get_manuals()

        if self.accept_json():
            return jsonify(self.get_result())
        self.get_template()

        return render_template(self.template_name, **self.context)

    def get_template(self):
        rol = self.context.get('rol')
        if not rol:
            return

        tlmp = {
            "isOperator": "operator.html",
            "isVerifier": "verifier.html",
        }
        self.template_name = tlmp.get(rol, self.template_name)

    def accept_json(self):
        if 'json' in request.headers.get('Accept', []):
            return True
        if "application/json" in request.headers.get("Content-Type", []):
            return True

        return False

    def get_ids(self, id_dpp):
        self.id_dpp = None
        self.chid = id_dpp

        if len(id_dpp.split(":")) == 2:
            self.id_dpp = id_dpp
            self.chid = id_dpp.split(':')[0]

    def get_rols(self):
        rols = session.get('rols')
        if not g.user.is_authenticated and not rols:
            return []

        if rols:
            self.context['rols'] = rols

        if 'dpp' not in app.blueprints.keys():
            return []

        if not session.get('token_dlt'):
            return []

        token_dlt = session.get('token_dlt')
        api_dlt = app.config.get('API_DLT')
        if not token_dlt or not api_dlt:
            return []

        api = API(api_dlt, token_dlt, "ethereum")

        result = api.check_user_roles()
        if result.get('Status') != 200:
            return []

        if 'Success' not in result.get('Data', {}).get('status'):
            return []

        rols = result.get('Data', {}).get('data', {})
        self.context['rols'] = [(k, k) for k, v in rols.items() if v]

    def get_rol(self):
        rols = self.context.get('rols', [])
        rol = len(rols) == 1 and rols[0][0] or None
        if 'rol' in request.args and not rol:
            rol = dict(rols).get(request.args.get('rol'))
        self.context['rol'] = rol

    def get_device(self):
        if self.id_dpp:
            self.dpp = Dpp.query.filter_by(key=self.id_dpp).one()
            device = self.dpp.device
        else:
            device = Device.query.filter_by(chid=self.chid, active=True).first()

        if not device:
            return flask.abort(404)

        placeholder = device.binding or device.placeholder
        device_abstract = placeholder and placeholder.binding or device
        device_real = placeholder and placeholder.device or device
        self.device = device_abstract
        components = self.device.components
        if self.dpp:
            components = self.dpp.snapshot.components

        self.context.update(
            {
                'placeholder': placeholder,
                'device': self.device,
                'device_abstract': device_abstract,
                'device_real': device_real,
                'components': components,
            }
        )

    def get_last_dpp(self):
        dpps = sorted(self.device.dpps, key=lambda x: x.created)
        self.context['last_dpp'] = dpps and dpps[-1] or ''
        return self.context['last_dpp']

    def get_before_dpp(self):
        if not self.dpp:
            self.context['before_dpp'] = ''
            return ''

        dpps = sorted(self.device.dpps, key=lambda x: x.created)
        before_dpp = ''
        for dpp in dpps:
            if dpp == self.dpp:
                break
            before_dpp = dpp

        self.context['before_dpp'] = before_dpp
        return before_dpp

    def get_result(self):
        components = []
        data = {
            'document': {},
            'dpp': self.id_dpp,
            'algorithm': ALGORITHM,
            'components': components,
            'manufacturer DPP': '',
        }
        result = {
            '@context': ['https://ereuse.org/dpp0.json'],
            'data': data,
        }

        if self.dpp:
            data['document'] = self.dpp.snapshot.json_hw
            last_dpp = self.get_last_dpp()
            url_last = ''
            if last_dpp:
                url_last = 'https://{host}/{did}'.format(
                    did=last_dpp.key, host=app.config.get('HOST')
                )
            data['url_last'] = url_last

            for c in self.dpp.snapshot.components:
                components.append({c.type: c.chid})
            return result

        dpps = []
        for d in self.device.dpps:
            rr = {
                'dpp': d.key,
                'document': d.snapshot.json_hw,
                'algorithm': ALGORITHM,
                'manufacturer DPP': '',
            }
            dpps.append(rr)
        return {
            '@context': ['https://ereuse.org/dpp0.json'],
            'data': dpps,
        }

    def get_manuals(self):
        manuals = {
            'ifixit': [],
            'icecat': [],
            'details': {},
            'laer': [],
            'energystar': {},
        }
        try:
            params = {
                "manufacturer": self.device.manufacturer,
                "model": self.device.model,
            }
            self.params = json.dumps(params)
            manuals['ifixit'] = self.request_manuals('ifixit')
            manuals['icecat'] = self.request_manuals('icecat')
            manuals['laer'] = self.request_manuals('laer')
            manuals['energystar'] = self.request_manuals('energystar') or {}
            if manuals['icecat']:
                manuals['details'] = manuals['icecat'][0]
        except Exception as err:
            logger.error("Error: {}".format(err))

        self.context['manuals'] = manuals
        self.parse_energystar()

    def parse_energystar(self):
        if not self.context.get('manuals', {}).get('energystar'):
            return

        # Defined in:
        # https://dev.socrata.com/foundry/data.energystar.gov/j7nq-iepp

        energy_types = [
            'functional_adder_allowances_kwh',
            'tec_allowance_kwh',
            'long_idle_watts',
            'short_idle_watts',
            'off_mode_watts',
            'sleep_mode_watts',
            'tec_of_model_kwh',
            'tec_requirement_kwh',
            'work_off_mode_watts',
            'work_weighted_power_of_model_watts',
        ]
        energy = {}
        for field in energy_types:
            energy[field] = []

        for e in self.context['manuals']['energystar']:
            for field in energy_types:
                for k, v in e.items():
                    if not v:
                        continue
                    if field in k:
                        energy[field].append(v)

        for k, v in energy.items():
            if not v:
                energy[k] = 0
                continue
            tt = sum([float(i) for i in v])
            energy[k] = round(tt / len(v), 2)

        self.context['manuals']['energystar'] = energy

    def request_manuals(self, prefix):
        url = app.config['URL_MANUALS']
        if not url:
            return {}

        res = requests.post(url + "/" + prefix, self.params)
        if res.status_code > 299:
            return {}

        try:
            response = res.json()
        except Exception:
            response = {}

        return response


did.add_url_rule('/<string:id_dpp>', view_func=DidView.as_view('did'))
