import flask
from flask.views import View
from flask import Blueprint, url_for
from flask_login import login_required, current_user

from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.inventory.forms import LotDeviceAddForm, LotForm

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


class LotDeviceListView(View):
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self, id):
        # TODO @cayop adding filter
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        lot = lots.filter(Lot.id == id).one()
        filter_types = ['Desktop', 'Laptop', 'Server']
        devices = [dev for dev in lot.devices if dev.type in filter_types]

        context = {'devices': devices,
                   'lots': lots,
                   'form_lot_device': LotDeviceAddForm(),
                   'lot': lot}
        return flask.render_template(self.template_name, **context)


class LotDeviceAddView(View):
    methods = ['POST']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self):
        form = LotDeviceAddForm()
        if form.validate_on_submit():
            form.save()

            next_url = url_for('inventory.devices.lotdevicelist', id=form.lot.id)
            return flask.redirect(next_url)


class LotView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/lot.html'
    title = "Add a new lot"

    def dispatch_request(self, id=None):
        if id:
            self.title = "Edit lot"
        form = LotForm(id=id)
        if form.validate_on_submit():
            form.save()
            next_url = url_for('inventory.devices.lotdevicelist', id=form.lot.id)
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, form=form, title=self.title)


devices.add_url_rule('/device/', view_func=DeviceListView.as_view('devicelist'))
devices.add_url_rule('/lot/<string:id>/device/', view_func=LotDeviceListView.as_view('lotdevicelist'))
devices.add_url_rule('/lot/devices/add/', view_func=LotDeviceAddView.as_view('lot_devices_add'))
devices.add_url_rule('/lot/add', view_func=LotView.as_view('lot_add'))
devices.add_url_rule('/lot/<string:id>/', view_func=LotView.as_view('lot_edit'))
