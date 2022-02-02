import flask
import datetime
from flask.views import View
from flask import Blueprint, url_for, request
from flask_login import login_required, current_user

from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.inventory.forms import LotDeviceForm, LotForm, UploadSnapshotForm, \
    NewDeviceForm, TagForm, TagUnnamedForm, TagDeviceForm, NewActionForm, AllocateForm

# TODO(@slamora): rename base 'inventory.devices' --> 'inventory'
devices = Blueprint('inventory.devices', __name__, url_prefix='/inventory')


class DeviceListMix(View):
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def get_context(self, lot_id):
        # TODO @cayop adding filter
        # https://github.com/eReuse/devicehub-teal/blob/testing/ereuse_devicehub/resources/device/views.py#L56
        filter_types = ['Desktop', 'Laptop', 'Server']
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        lot = None
        tags = Tag.query.filter(Tag.owner_id == current_user.id).filter(
            Tag.device_id == None).order_by(Tag.created.desc())

        if lot_id:
            lot = lots.filter(Lot.id == lot_id).one()
            devices = [dev for dev in lot.devices if dev.type in filter_types]
            devices = sorted(devices, key=lambda x: x.updated, reverse=True)
            form_new_action = NewActionForm(lot=lot.id)
            form_new_allocate = AllocateForm(lot=lot.id)
        else:
            devices = Device.query.filter(
                Device.owner_id == current_user.id).filter(
                Device.type.in_(filter_types)).filter(Device.lots == None).order_by(
                    Device.updated.desc())
            form_new_action = NewActionForm()
            form_new_allocate = AllocateForm()

        self.context = {
            'devices': devices,
            'lots': lots,
            'form_lot_device': LotDeviceForm(),
            'form_tag_device': TagDeviceForm(),
            'form_new_action': form_new_action,
            'form_new_allocate': form_new_allocate,
            'lot': lot,
            'tags': tags
        }

        return self.context


class DeviceListView(DeviceListMix):

    def dispatch_request(self, lot_id=None):
        self.get_context(lot_id)
        return flask.render_template(self.template_name, **self.context)


class DeviceDetailView(View):
    decorators = [login_required]
    template_name = 'inventory/device_detail.html'

    def dispatch_request(self, id):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        device = Device.query.filter(
            Device.owner_id == current_user.id).filter(Device.devicehub_id == id).one()

        context = {
            'device': device,
            'lots': lots,
            'page_title': 'Device {}'.format(device.devicehub_id),
        }
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
        context = {'page_title': 'Upload Snapshot'}
        lots = Lot.query.filter(Lot.owner_id == current_user.id).all()
        form = UploadSnapshotForm()
        if form.validate_on_submit():
            form.save()

        return flask.render_template(self.template_name, form=form, lots=lots, **context)


class DeviceCreateView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/device_create.html'

    def dispatch_request(self):
        context = {'page_title': 'New Device'}
        lots = Lot.query.filter(Lot.owner_id == current_user.id).all()
        form = NewDeviceForm()
        if form.validate_on_submit():
            form.save()
            next_url = url_for('inventory.devices.devicelist')
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, form=form, lots=lots, **context)


class TagListView(View):
    methods = ['GET']
    decorators = [login_required]
    template_name = 'inventory/tag_list.html'

    def dispatch_request(self):
        tags = Tag.query.filter(Tag.owner_id == current_user.id)
        context = {
            'lots': [],
            'tags': tags,
            'page_title': 'Tags Management',
        }
        return flask.render_template(self.template_name, **context)


class TagAddView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/tag_create.html'

    def dispatch_request(self):
        context = {'page_title': 'New Tag'}
        form = TagForm()
        if form.validate_on_submit():
            form.save()
            next_url = url_for('inventory.devices.taglist')
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, form=form, **context)


class TagAddUnnamedView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/tag_create_unnamed.html'

    def dispatch_request(self):
        context = {'page_title': 'New Unnamed Tag'}
        form = TagUnnamedForm()
        if form.validate_on_submit():
            form.save()
            next_url = url_for('inventory.devices.taglist')
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, form=form, **context)


class TagDetailView(View):
    decorators = [login_required]
    template_name = 'inventory/tag_detail.html'

    def dispatch_request(self, id):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        tag = Tag.query.filter(
            Tag.owner_id == current_user.id).filter(Tag.id == id).one()

        context = {
            'lots': lots,
            'tag': tag,
            'page_title': '{} Tag'.format(tag.code),
        }
        return flask.render_template(self.template_name, **context)


class TagLinkDeviceView(View):
    methods = ['POST']
    decorators = [login_required]
    # template_name = 'inventory/device_list.html'

    def dispatch_request(self):
        form = TagDeviceForm()
        if form.validate_on_submit():
            form.save()

            return flask.redirect(request.referrer)


class TagUnlinkDeviceView(View):
    methods = ['POST', 'GET']
    decorators = [login_required]
    template_name = 'inventory/tag_unlink_device.html'

    def dispatch_request(self, id):
        form = TagDeviceForm(delete=True, device=id)
        if form.validate_on_submit():
            form.remove()

            next_url = url_for('inventory.devices.devicelist')
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, form=form, referrer=request.referrer)


class NewActionView(View):
    methods = ['POST']
    decorators = [login_required]
    _form = NewActionForm

    def dispatch_request(self):
        self.form = self._form()
        if self.form.validate_on_submit():
            self.form.save()
            next_url = request.referrer or url_for('inventory.devices.devicelist')
            return flask.redirect(next_url)


class NewAllocateView(NewActionView, DeviceListMix):
    methods = ['POST']
    _form = AllocateForm

    def dispatch_request(self):
        dispatch = super().dispatch_request()
        if dispatch:
            return dispatch

        # lot_id = self.form.lot.data
        # FIXME
        # import pdb; pdb.set_trace()
        self.get_context(None)
        self.context['form_new_allocate'] = self.form
        return flask.render_template(self.template_name, **self.context)


devices.add_url_rule('/action/add/', view_func=NewActionView.as_view('action_add'))
devices.add_url_rule('/action/allocate/add/', view_func=NewAllocateView.as_view('allocate_add'))
devices.add_url_rule('/device/', view_func=DeviceListView.as_view('devicelist'))
devices.add_url_rule('/device/<string:id>/', view_func=DeviceDetailView.as_view('device_details'))
devices.add_url_rule('/lot/<string:lot_id>/device/', view_func=DeviceListView.as_view('lotdevicelist'))
devices.add_url_rule('/lot/devices/add/', view_func=LotDeviceAddView.as_view('lot_devices_add'))
devices.add_url_rule('/lot/devices/del/', view_func=LotDeviceDeleteView.as_view('lot_devices_del'))
devices.add_url_rule('/lot/add/', view_func=LotCreateView.as_view('lot_add'))
devices.add_url_rule('/lot/<string:id>/del/', view_func=LotDeleteView.as_view('lot_del'))
devices.add_url_rule('/lot/<string:id>/', view_func=LotUpdateView.as_view('lot_edit'))
devices.add_url_rule('/upload-snapshot/', view_func=UploadSnapshotView.as_view('upload_snapshot'))
devices.add_url_rule('/device/add/', view_func=DeviceCreateView.as_view('device_add'))
devices.add_url_rule('/tag/', view_func=TagListView.as_view('taglist'))
devices.add_url_rule('/tag/add/', view_func=TagAddView.as_view('tag_add'))
devices.add_url_rule('/tag/unnamed/add/', view_func=TagAddUnnamedView.as_view('tag_unnamed_add'))
devices.add_url_rule('/tag/<string:id>/', view_func=TagDetailView.as_view('tag_details'))
devices.add_url_rule('/tag/devices/add/', view_func=TagLinkDeviceView.as_view('tag_devices_add'))
devices.add_url_rule('/tag/devices/<int:id>/del/', view_func=TagUnlinkDeviceView.as_view('tag_devices_del'))
