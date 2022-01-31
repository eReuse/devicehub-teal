import flask
import datetime
from flask.views import View
from flask import Blueprint, url_for, request
from flask_login import login_required, current_user

from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.inventory.forms import LotDeviceForm, LotForm, UploadSnapshotForm, NewDeviceForm, \
                                             NewActionForm, AllocateForm

devices = Blueprint('inventory.devices', __name__, url_prefix='/inventory')


class DeviceListView(View):
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self, lot_id=None):
        # TODO @cayop adding filter
        # https://github.com/eReuse/devicehub-teal/blob/testing/ereuse_devicehub/resources/device/views.py#L56
        filter_types = ['Desktop', 'Laptop', 'Server']
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        lot = None
        if lot_id:
            lot = lots.filter(Lot.id == lot_id).one()
            devices = [dev for dev in lot.devices if dev.type in filter_types]
            devices = sorted(devices, key=lambda x: x.updated, reverse=True)
            form_new_action = NewActionForm(lot=lot.id)
        else:
            devices = Device.query.filter(
                Device.owner_id == current_user.id).filter(
                Device.type.in_(filter_types)).filter(Device.lots == None).order_by(
                    Device.updated.desc())
            form_new_action = NewActionForm()

        allocate = AllocateForm(start_time=datetime.datetime.now(),
                                end_time=datetime.datetime.now()+datetime.timedelta(1))

        context = {'devices': devices,
                   'lots': lots,
                   'form_lot_device': LotDeviceForm(),
                   'form_new_action': form_new_action,
                   'form_allocate': allocate,
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

            next_url = request.referrer or url_for('inventory.devices.devicelist')
            return flask.redirect(next_url)


class LotDeviceDeleteView(View):
    methods = ['POST']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self):
        form = LotDeviceForm()
        if form.validate_on_submit():
            form.remove()

            next_url = request.referrer or url_for('inventory.devices.devicelist')
            return flask.redirect(next_url)


class LotCreateView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/lot.html'
    title = "Add a new lot"

    def dispatch_request(self):
        form = LotForm()
        if form.validate_on_submit():
            form.save()
            next_url = url_for('inventory.devices.lotdevicelist', lot_id=form.id)
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
            next_url = url_for('inventory.devices.lotdevicelist', lot_id=id)
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


class CreateDeviceView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/create_device.html'

    def dispatch_request(self):
        lots = Lot.query.filter(Lot.owner_id == current_user.id).all()
        form = NewDeviceForm()
        if form.validate_on_submit():
            form.save()
            next_url = url_for('inventory.devices.devicelist')
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, form=form, lots=lots)


class NewActionView(View):
    methods = ['POST']
    decorators = [login_required]

    def dispatch_request(self):
        form = NewActionForm()
        # import pdb; pdb.set_trace()
        next_url = url_for('inventory.devices.devicelist')
        if form.validate_on_submit():
            # form.save()
            if form.lot.data:
                next_url = url_for('inventory.devices.lotdevicelist', id=form.lot.data)

            return flask.redirect(next_url)


devices.add_url_rule('/action/add/', view_func=NewActionView.as_view('action_add'))
devices.add_url_rule('/device/', view_func=DeviceListView.as_view('devicelist'))
devices.add_url_rule('/device/<string:id>/', view_func=DeviceDetailsView.as_view('device_details'))
devices.add_url_rule('/lot/<string:lot_id>/device/', view_func=DeviceListView.as_view('lotdevicelist'))
devices.add_url_rule('/lot/devices/add/', view_func=LotDeviceAddView.as_view('lot_devices_add'))
devices.add_url_rule('/lot/devices/del/', view_func=LotDeviceDeleteView.as_view('lot_devices_del'))
devices.add_url_rule('/lot/add/', view_func=LotCreateView.as_view('lot_add'))
devices.add_url_rule('/lot/<string:id>/del/', view_func=LotDeleteView.as_view('lot_del'))
devices.add_url_rule('/lot/<string:id>/', view_func=LotUpdateView.as_view('lot_edit'))
devices.add_url_rule('/upload-snapshot/', view_func=UploadSnapshotView.as_view('upload_snapshot'))
devices.add_url_rule('/device/add/', view_func=CreateDeviceView.as_view('device_add'))
