import flask
from flask.views import View
from flask import Blueprint, url_for
from flask_login import login_required, current_user

from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.inventory.forms import LotDeviceForm, LotForm, NewActionForm

devices = Blueprint('inventory.devices', __name__, url_prefix='/inventory')


class DeviceListView(View):
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self, id=None):
        # TODO @cayop adding filter
        filter_types = ['Desktop', 'Laptop', 'Server']
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        lot = None
        if id:
            lot = lots.filter(Lot.id == id).one()
            devices = [dev for dev in lot.devices if dev.type in filter_types]
            form_new_action = NewActionForm(lot=lot.id)
        else:
            devices = Device.query.filter(
                Device.owner_id == current_user.id).filter(
                Device.type.in_(filter_types))
            form_new_action = NewActionForm()

        context = {'devices': devices,
                   'lots': lots,
                   'form_lot_device': LotDeviceForm(),
                   'form_new_action': form_new_action,
                   'lot': lot}
        return flask.render_template(self.template_name, **context)


class LotDeviceAddView(View):
    methods = ['POST']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self):
        form = LotDeviceForm()
        if form.validate_on_submit():
            form.save()

            next_url = url_for('inventory.devices.lotdevicelist', id=form.lot.data)
            return flask.redirect(next_url)


class LotDeviceDeleteView(View):
    methods = ['POST']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self):
        form = LotDeviceForm()
        if form.validate_on_submit():
            form.remove()

            next_url = url_for('inventory.devices.lotdevicelist', id=form.lot.data)
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
            lot_id = id
            if not id:
                lot_id = form.instance.id
            next_url = url_for('inventory.devices.lotdevicelist', id=lot_id)
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, form=form, title=self.title)


class LotDeleteView(View):
    methods = ['GET']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self, id):
        form = LotForm(id=id)
        form.remove()
        next_url = url_for('inventory.devices.devicelist')
        return flask.redirect(next_url)


class NewActionView(View):
    methods = ['POST']
    decorators = [login_required]

    def dispatch_request(self):
        form = NewActionForm()
        next_url = url_for('inventory.devices.devicelist')
        if form.validate_on_submit():
            form.save()
            if form.lot.data:
                next_url = url_for('inventory.devices.lotdevicelist', id=form.lot.data)

            return flask.redirect(next_url)


devices.add_url_rule('/action/add/', view_func=NewActionView.as_view('action_add'))
devices.add_url_rule('/device/', view_func=DeviceListView.as_view('devicelist'))
devices.add_url_rule('/lot/<string:id>/device/', view_func=DeviceListView.as_view('lotdevicelist'))
devices.add_url_rule('/lot/devices/add/', view_func=LotDeviceAddView.as_view('lot_devices_add'))
devices.add_url_rule('/lot/devices/del/', view_func=LotDeviceDeleteView.as_view('lot_devices_del'))
devices.add_url_rule('/lot/add/', view_func=LotView.as_view('lot_add'))
devices.add_url_rule('/lot/<string:id>/del/', view_func=LotDeleteView.as_view('lot_del'))
devices.add_url_rule('/lot/<string:id>/', view_func=LotView.as_view('lot_edit'))
