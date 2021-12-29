import flask
from flask import Blueprint
from flask.views import View
from flask_login import login_required, current_user

from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.lot.models import Lot

devices = Blueprint('inventory.devices', __name__, url_prefix='/inventory')


class DeviceListView(View):
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self):
        # TODO @cayop adding filter
        filter_types = ['Desktop', 'Laptop', 'Server']
        devices = Device.query.filter(
            Device.owner_id == current_user.id).filter(
            Device.type.in_(filter_types))

        lots = Lot.query.filter(Lot.owner_id == current_user.id)

        context = {'devices': devices, 'lots': lots}
        return flask.render_template(self.template_name, **context)


devices.add_url_rule('/device/', view_func=DeviceListView.as_view('devicelist'))
