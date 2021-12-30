import flask
from flask.views import View
from flask import Blueprint, url_for, g
from flask_login import login_required, current_user

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.inventory.forms import LotDeviceAddForm

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

        context = {'devices': devices, 'lots': lots, 'form_lot_device': LotDeviceAddForm()}
        return flask.render_template(self.template_name, **context)


class LotDeviceAddView(View):
    methods = ['POST']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self):
        form = LotDeviceAddForm()
        if form.validate_on_submit():
            lot = form.lot
            devices = form.devices
            lot.devices.update(devices)
            g.user = current_user
            db.session.add(lot)
            db.session().final_flush()

            next_url = url_for('inventory.devices.devicelist')
            # next_url = url_for('inventory.devices.lot')
            return flask.redirect(next_url)


devices.add_url_rule('/device/', view_func=DeviceListView.as_view('devicelist'))
devices.add_url_rule('/lot/devices/add', view_func=LotDeviceAddView.as_view('lot_devices_add'))
