import flask
from flask import Blueprint
from flask.views import View
from flask_login import login_required, login_user

from ereuse_devicehub.forms import LoginForm
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.utils import is_safe_url

devices = Blueprint('devices', __name__)


class DeviceListView(View):
    # decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self):
        context = {}
        return flask.render_template(self.template_name, **context)


devices.add_url_rule('/inventory/device/list/', view_func=DeviceListView.as_view('devicelist'))
