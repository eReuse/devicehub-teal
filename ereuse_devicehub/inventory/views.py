import flask
from flask.views import View
from flask import Blueprint, url_for, request
from flask_login import login_required, current_user

from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.inventory.forms import LotDeviceForm, LotForm, UploadSnapshotForm
from ereuse_devicehub.resources.action import SnapshotDef
from ereuse_devicehub.resources.action.views.snapshot import SnapshotView as TealSnapshotView

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
            devices = sorted(devices, key=lambda x: x.updated, reverse=True)
        else:
            devices = Device.query.filter(
                Device.owner_id == current_user.id).filter(
                Device.type.in_(filter_types)).filter(Device.lots == None).order_by(
                    Device.updated.desc())

        context = {'devices': devices,
                   'lots': lots,
                   'form_lot_device': LotDeviceForm(),
                   'lot': lot}
        return flask.render_template(self.template_name, **context)


class DeviceDetailsView(View):
    decorators = [login_required]
    template_name = 'inventory/device_details.html'

    def dispatch_request(self, id):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        device = Device.query.filter(
                     Device.owner_id == current_user.id).filter(Device.devicehub_id == id).one()

        context = {'device': device,
                   'lots': lots}
        return flask.render_template(self.template_name, **context)


class LotDeviceAddView(View):
    methods = ['POST']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self):
        form = LotDeviceForm()
        if form.validate_on_submit():
            form.save()

            return flask.redirect(request.referrer)


class LotDeviceDeleteView(View):
    methods = ['POST']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self):
        form = LotDeviceForm()
        if form.validate_on_submit():
            form.remove()

            # TODO @cayop It's possible this redirect not work in production
            return flask.redirect(request.referrer)


class LotCreateView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/lot.html'
    title = "Add a new lot"

    def dispatch_request(self):
        form = LotForm()
        if form.validate_on_submit():
            form.save()
            next_url = url_for('inventory.devices.lotdevicelist', id=form.id)
            return flask.redirect(next_url)

        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        return flask.render_template(self.template_name, form=form, title=self.title, lots=lots)


class LotUpdateView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/lot.html'
    title = "Edit a new lot"

    def dispatch_request(self, id):
        form = LotForm(id=id)
        if form.validate_on_submit():
            form.save()
            next_url = url_for('inventory.devices.lotdevicelist', id=id)
            return flask.redirect(next_url)

        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        return flask.render_template(self.template_name, form=form, title=self.title, lots=lots)


class LotDeleteView(View):
    methods = ['GET']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self, id):
        form = LotForm(id=id)
        form.remove()
        next_url = url_for('inventory.devices.devicelist')
        return flask.redirect(next_url)


class UploadSnapshotView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/upload_snapshot.html'

    def dispatch_request(self):
        lots = Lot.query.filter(Lot.owner_id == current_user.id).all()
        form = UploadSnapshotForm()
        if form.validate_on_submit():
            form.save()

        return flask.render_template(self.template_name, form=form, lots=lots)


devices.add_url_rule('/device/', view_func=DeviceListView.as_view('devicelist'))
devices.add_url_rule('/device/<string:id>/', view_func=DeviceDetailsView.as_view('device_details'))
devices.add_url_rule('/lot/<string:id>/device/', view_func=DeviceListView.as_view('lotdevicelist'))
devices.add_url_rule('/lot/devices/add/', view_func=LotDeviceAddView.as_view('lot_devices_add'))
devices.add_url_rule('/lot/devices/del/', view_func=LotDeviceDeleteView.as_view('lot_devices_del'))
devices.add_url_rule('/lot/add/', view_func=LotCreateView.as_view('lot_add'))
devices.add_url_rule('/lot/<string:id>/del/', view_func=LotDeleteView.as_view('lot_del'))
devices.add_url_rule('/lot/<string:id>/', view_func=LotUpdateView.as_view('lot_edit'))
devices.add_url_rule('/upload-snapshot/', view_func=UploadSnapshotView.as_view('upload_snapshot'))
