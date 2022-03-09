import csv
import logging
from io import StringIO

import flask
import flask_weasyprint
from flask import Blueprint, g, make_response, request, url_for
from flask.views import View
from flask_login import current_user, login_required
from requests.exceptions import ConnectionError
from sqlalchemy import or_
from werkzeug.exceptions import NotFound

from ereuse_devicehub import messages
from ereuse_devicehub.db import db
from ereuse_devicehub.inventory.forms import (
    AllocateForm,
    DataWipeForm,
    FilterForm,
    LotDeviceForm,
    LotDeviceShowForm,
    LotForm,
    NewActionForm,
    NewDeviceForm,
    TagDeviceForm,
    TagForm,
    TagUnnamedForm,
    TradeDocumentForm,
    TradeForm,
    UploadSnapshotForm,
)
from ereuse_devicehub.resources.action.models import Trade
from ereuse_devicehub.resources.device.models import Computer, DataStorage, Device
from ereuse_devicehub.resources.documents.device_row import ActionRow, DeviceRow
from ereuse_devicehub.resources.hash_reports import insert_hash
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.tag.model import Tag

# TODO(@slamora): rename base 'inventory.devices' --> 'inventory'
devices = Blueprint('inventory.devices', __name__, url_prefix='/inventory')

logger = logging.getLogger(__name__)


class GenericMixView(View):
    def get_lots(self):
        return (
            Lot.query.outerjoin(Trade)
            .filter(
                or_(
                    Trade.user_from == g.user,
                    Trade.user_to == g.user,
                    Lot.owner_id == g.user.id,
                )
            )
            .distinct()
        )


class DeviceListMix(GenericMixView):
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def get_context(self, lot_id):
        form_filter = FilterForm()
        filter_types = form_filter.search()
        lots = self.get_lots()
        lot = None
        tags = (
            Tag.query.filter(Tag.owner_id == current_user.id)
            .filter(Tag.device_id.is_(None))
            .order_by(Tag.id.asc())
        )

        if lot_id:
            lot = lots.filter(Lot.id == lot_id).one()
            devices = lot.devices
            if "All" not in filter_types:
                devices = [dev for dev in lot.devices if dev.type in filter_types]
            devices = sorted(devices, key=lambda x: x.updated, reverse=True)
            form_new_action = NewActionForm(lot=lot.id)
            form_new_allocate = AllocateForm(lot=lot.id)
            form_new_datawipe = DataWipeForm(lot=lot.id)
            form_new_trade = TradeForm(
                lot=lot.id,
                user_to=g.user.email,
                user_from=g.user.email,
            )
        else:
            if "All" in filter_types:
                devices = (
                    Device.query.filter(Device.owner_id == current_user.id)
                    .filter_by(lots=None)
                    .order_by(Device.updated.desc())
                )
            else:
                devices = (
                    Device.query.filter(Device.owner_id == current_user.id)
                    .filter_by(lots=None)
                    .filter(Device.type.in_(filter_types))
                    .order_by(Device.updated.desc())
                )

            form_new_action = NewActionForm()
            form_new_allocate = AllocateForm()
            form_new_datawipe = DataWipeForm()
            form_new_trade = ''
        action_devices = form_new_action.devices.data
        list_devices = []
        if action_devices:
            list_devices.extend([int(x) for x in action_devices.split(",")])

        self.context = {
            'devices': devices,
            'lots': lots,
            'form_lot_device': LotDeviceForm(),
            'form_tag_device': TagDeviceForm(),
            'form_new_action': form_new_action,
            'form_new_allocate': form_new_allocate,
            'form_new_datawipe': form_new_datawipe,
            'form_new_trade': form_new_trade,
            'form_filter': form_filter,
            'form_lot_device_del': LotDeviceShowForm(),
            'lot': lot,
            'tags': tags,
            'list_devices': list_devices,
        }

        return self.context


class DeviceListView(DeviceListMix):
    def dispatch_request(self, lot_id=None):
        self.get_context(lot_id)
        return flask.render_template(self.template_name, **self.context)


class DeviceDetailView(GenericMixView):
    decorators = [login_required]
    template_name = 'inventory/device_detail.html'

    def dispatch_request(self, id):
        lots = self.get_lots()
        device = (
            Device.query.filter(Device.owner_id == current_user.id)
            .filter(Device.devicehub_id == id)
            .one()
        )

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
            form.save(commit=False)
            messages.success(
                'Add devices to lot "{}" successfully!'.format(form._lot.name)
            )
            db.session.commit()
        else:
            messages.error('Error adding devices to lot!')

        next_url = request.referrer or url_for('inventory.devices.devicelist')
        return flask.redirect(next_url)


class LotDeviceDeleteShowView(GenericMixView):
    methods = ['POST']
    decorators = [login_required]
    template_name = 'inventory/removeDeviceslot2.html'
    title = 'Remove from a lot'

    def dispatch_request(self, lot_id=None):
        # import pdb; pdb.set_trace()
        next_url = request.referrer or url_for('inventory.devices.devicelist')
        form = LotDeviceShowForm()
        if not form.validate_on_submit():
            messages.error('Error, you need select one or more devices!')
            if lot_id:
                next_url = url_for('inventory.devices.lotdevicelist', lot_id=form.id)

            return flask.redirect(next_url)

        lots = self.get_lots()
        form_lot = LotDeviceForm(devices=form.devices)
        context = {'form': form_lot, 'title': self.title, 'lots': lots}
        return flask.render_template(self.template_name, **context)


class LotDeviceDeleteView(View):
    methods = ['POST']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self):
        form = LotDeviceForm()
        if form.validate_on_submit():
            form.remove(commit=False)
            messages.success(
                'Remove devices from lot "{}" successfully!'.format(form._lot.name)
            )
            db.session.commit()
        else:
            messages.error('Error removing devices from lot!')

        next_url = request.referrer or url_for('inventory.devices.devicelist')
        return flask.redirect(next_url)


class LotCreateView(GenericMixView):
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

        lots = self.get_lots()
        context = {'form': form, 'title': self.title, 'lots': lots}
        return flask.render_template(self.template_name, **context)


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
        context = {'form': form, 'title': self.title, 'lots': lots}
        return flask.render_template(self.template_name, **context)


class LotDeleteView(View):
    methods = ['GET']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self, id):
        form = LotForm(id=id)
        if form.instance.trade:
            msg = "Sorry, the lot cannot be deleted because have a trade action "
            messages.error(msg)
            next_url = url_for('inventory.devices.lotdevicelist', lot_id=id)
            return flask.redirect(next_url)

        form.remove()
        next_url = url_for('inventory.devices.devicelist')
        return flask.redirect(next_url)


class UploadSnapshotView(GenericMixView):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/upload_snapshot.html'

    def dispatch_request(self, lot_id=None):
        lots = self.get_lots()
        form = UploadSnapshotForm()
        context = {
            'page_title': 'Upload Snapshot',
            'lots': lots,
            'form': form,
            'lot_id': lot_id,
        }
        if form.validate_on_submit():
            snapshot = form.save(commit=False)
            if lot_id:
                lot = lots.filter(Lot.id == lot_id).one()
                lot.devices.add(snapshot.device)
                db.session.add(lot)
            db.session.commit()

        return flask.render_template(self.template_name, **context)


class DeviceCreateView(GenericMixView):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/device_create.html'

    def dispatch_request(self, lot_id=None):
        lots = self.get_lots()
        form = NewDeviceForm()
        context = {
            'page_title': 'New Device',
            'lots': lots,
            'form': form,
            'lot_id': lot_id,
        }
        if form.validate_on_submit():
            snapshot = form.save(commit=False)
            next_url = url_for('inventory.devices.devicelist')
            if lot_id:
                next_url = url_for('inventory.devices.lotdevicelist', lot_id=lot_id)
                lot = lots.filter(Lot.id == lot_id).one()
                lot.devices.add(snapshot.device)
                db.session.add(lot)

            db.session.commit()
            messages.success('Device "{}" created successfully!'.format(form.type.data))
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, **context)


class TagListView(View):
    methods = ['GET']
    decorators = [login_required]
    template_name = 'inventory/tag_list.html'

    def dispatch_request(self):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        tags = Tag.query.filter(Tag.owner_id == current_user.id).order_by(Tag.id)
        context = {
            'lots': lots,
            'tags': tags,
            'page_title': 'Tags Management',
        }
        return flask.render_template(self.template_name, **context)


class TagAddView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/tag_create.html'

    def dispatch_request(self):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        context = {'page_title': 'New Tag', 'lots': lots}
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
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        context = {'page_title': 'New Unnamed Tag', 'lots': lots}
        form = TagUnnamedForm()
        if form.validate_on_submit():
            try:
                form.save()
            except ConnectionError as e:
                logger.error(
                    "Error while trying to connect to tag server: {}".format(e)
                )
                msg = (
                    "Sorry, we cannot create the unnamed tags requested because "
                    "some error happens while connecting to the tag server!"
                )
                messages.error(msg)

            next_url = url_for('inventory.devices.taglist')
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, form=form, **context)


class TagDetailView(View):
    decorators = [login_required]
    template_name = 'inventory/tag_detail.html'

    def dispatch_request(self, id):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        tag = (
            Tag.query.filter(Tag.owner_id == current_user.id).filter(Tag.id == id).one()
        )

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
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        form = TagDeviceForm(delete=True, device=id)
        if form.validate_on_submit():
            form.remove()

            next_url = url_for('inventory.devices.devicelist')
            return flask.redirect(next_url)

        return flask.render_template(
            self.template_name, form=form, lots=lots, referrer=request.referrer
        )


class NewActionView(View):
    methods = ['POST']
    decorators = [login_required]
    form_class = NewActionForm

    def dispatch_request(self):
        self.form = self.form_class()

        if self.form.validate_on_submit():
            self.form.save()
            messages.success(
                'Action "{}" created successfully!'.format(self.form.type.data)
            )

            next_url = self.get_next_url()
            return flask.redirect(next_url)

    def get_next_url(self):
        lot_id = self.form.lot.data

        if lot_id:
            return url_for('inventory.devices.lotdevicelist', lot_id=lot_id)

        return url_for('inventory.devices.devicelist')


class NewAllocateView(NewActionView, DeviceListMix):
    methods = ['POST']
    form_class = AllocateForm

    def dispatch_request(self):
        self.form = self.form_class()

        if self.form.validate_on_submit():
            self.form.save()
            messages.success(
                'Action "{}" created successfully!'.format(self.form.type.data)
            )

            next_url = self.get_next_url()
            return flask.redirect(next_url)

        lot_id = self.form.lot.data
        self.get_context(lot_id)
        self.context['form_new_allocate'] = self.form
        return flask.render_template(self.template_name, **self.context)


class NewDataWipeView(NewActionView, DeviceListMix):
    methods = ['POST']
    form_class = DataWipeForm

    def dispatch_request(self):
        self.form = self.form_class()

        if self.form.validate_on_submit():
            self.form.save()
            messages.success(
                'Action "{}" created successfully!'.format(self.form.type.data)
            )

            next_url = self.get_next_url()
            return flask.redirect(next_url)

        lot_id = self.form.lot.data
        self.get_context(lot_id)
        self.context['form_new_datawipe'] = self.form
        return flask.render_template(self.template_name, **self.context)


class NewTradeView(NewActionView, DeviceListMix):
    methods = ['POST']
    form_class = TradeForm

    def dispatch_request(self):
        self.form = self.form_class()

        if self.form.validate_on_submit():
            self.form.save()
            messages.success(
                'Action "{}" created successfully!'.format(self.form.type.data)
            )

            next_url = self.get_next_url()
            return flask.redirect(next_url)

        lot_id = self.form.lot.data
        self.get_context(lot_id)
        self.context['form_new_trade'] = self.form
        return flask.render_template(self.template_name, **self.context)


class NewTradeDocumentView(View):
    methods = ['POST', 'GET']
    decorators = [login_required]
    template_name = 'inventory/trade_document.html'
    form_class = TradeDocumentForm
    title = "Add new document"

    def dispatch_request(self, lot_id):
        self.form = self.form_class(lot=lot_id)

        if self.form.validate_on_submit():
            self.form.save()
            messages.success('Document created successfully!')
            next_url = url_for('inventory.devices.lotdevicelist', lot_id=lot_id)
            return flask.redirect(next_url)

        return flask.render_template(
            self.template_name, form=self.form, title=self.title
        )


class ExportsView(View):
    methods = ['GET']
    decorators = [login_required]

    def dispatch_request(self, export_id):
        export_ids = {
            'metrics': self.metrics,
            'devices': self.devices_list,
            'certificates': self.erasure,
            'links': self.public_links,
        }

        if export_id not in export_ids:
            return NotFound()
        return export_ids[export_id]()

    def find_devices(self):
        args = request.args.get('ids')
        ids = args.split(',') if args else []
        query = Device.query.filter(Device.owner == g.user)
        return query.filter(Device.devicehub_id.in_(ids))

    def response_csv(self, data, name):
        bfile = data.getvalue().encode('utf-8')
        # insert proof
        insert_hash(bfile)
        output = make_response(bfile)
        output.headers['Content-Disposition'] = 'attachment; filename={}'.format(name)
        output.headers['Content-type'] = 'text/csv'
        return output

    def devices_list(self):
        """Get device query and put information in csv format."""
        data = StringIO()
        cw = csv.writer(data, delimiter=';', lineterminator="\n", quotechar='"')
        first = True

        for device in self.find_devices():
            d = DeviceRow(device, {})
            if first:
                cw.writerow(d.keys())
                first = False
            cw.writerow(d.values())

        return self.response_csv(data, "export.csv")

    def metrics(self):
        """Get device query and put information in csv format."""
        data = StringIO()
        cw = csv.writer(data, delimiter=';', lineterminator="\n", quotechar='"')
        first = True
        devs_id = []
        # Get the allocate info
        for device in self.find_devices():
            devs_id.append(device.id)
            for allocate in device.get_metrics():
                d = ActionRow(allocate)
                if first:
                    cw.writerow(d.keys())
                    first = False
                cw.writerow(d.values())

        # Get the trade info
        query_trade = Trade.query.filter(
            Trade.devices.any(Device.id.in_(devs_id))
        ).all()

        lot_id = request.args.get('lot')
        if lot_id and not query_trade:
            lot = Lot.query.filter_by(id=lot_id).one()
            if hasattr(lot, "trade") and lot.trade:
                if g.user in [lot.trade.user_from, lot.trade.user_to]:
                    query_trade = [lot.trade]

        for trade in query_trade:
            data_rows = trade.get_metrics()
            for row in data_rows:
                d = ActionRow(row)
                if first:
                    cw.writerow(d.keys())
                    first = False
                cw.writerow(d.values())

        return self.response_csv(data, "actions_export.csv")

    def public_links(self):
        # get a csv with the publink links of this devices
        data = StringIO()
        cw = csv.writer(data, delimiter=';', lineterminator="\n", quotechar='"')
        cw.writerow(['links'])
        host_url = request.host_url
        for dev in self.find_devices():
            code = dev.devicehub_id
            link = [f"{host_url}devices/{code}"]
            cw.writerow(link)

        return self.response_csv(data, "links.csv")

    def erasure(self):
        template = self.build_erasure_certificate()
        res = flask_weasyprint.render_pdf(
            flask_weasyprint.HTML(string=template),
            download_filename='erasure-certificate.pdf',
        )
        insert_hash(res.data)
        return res

    def build_erasure_certificate(self):
        erasures = []
        for device in self.find_devices():
            if isinstance(device, Computer):
                for privacy in device.privacy:
                    erasures.append(privacy)
            elif isinstance(device, DataStorage):
                if device.privacy:
                    erasures.append(device.privacy)

        params = {
            'title': 'Erasure Certificate',
            'erasures': tuple(erasures),
            'url_pdf': '',
        }
        return flask.render_template('inventory/erasure.html', **params)


devices.add_url_rule('/action/add/', view_func=NewActionView.as_view('action_add'))
devices.add_url_rule('/action/trade/add/', view_func=NewTradeView.as_view('trade_add'))
devices.add_url_rule(
    '/action/allocate/add/', view_func=NewAllocateView.as_view('allocate_add')
)
devices.add_url_rule(
    '/action/datawipe/add/', view_func=NewDataWipeView.as_view('datawipe_add')
)
devices.add_url_rule(
    '/lot/<string:lot_id>/trade-document/add/',
    view_func=NewTradeDocumentView.as_view('trade_document_add'),
)
devices.add_url_rule('/device/', view_func=DeviceListView.as_view('devicelist'))
devices.add_url_rule(
    '/device/<string:id>/', view_func=DeviceDetailView.as_view('device_details')
)
devices.add_url_rule(
    '/lot/<string:lot_id>/device/', view_func=DeviceListView.as_view('lotdevicelist')
)
devices.add_url_rule(
    '/lot/devices/add/', view_func=LotDeviceAddView.as_view('lot_devices_add')
)
devices.add_url_rule(
    '/lot/devices/del/', view_func=LotDeviceDeleteView.as_view('lot_devices_del')
)
devices.add_url_rule(
    '/lot/devices/del/show',
    view_func=LotDeviceDeleteShowView.as_view('lot_devices_del_show'),
)
devices.add_url_rule('/lot/add/', view_func=LotCreateView.as_view('lot_add'))
devices.add_url_rule(
    '/lot/<string:id>/del/', view_func=LotDeleteView.as_view('lot_del')
)
devices.add_url_rule('/lot/<string:id>/', view_func=LotUpdateView.as_view('lot_edit'))
devices.add_url_rule(
    '/upload-snapshot/', view_func=UploadSnapshotView.as_view('upload_snapshot')
)
devices.add_url_rule(
    '/lot/<string:lot_id>/upload-snapshot/',
    view_func=UploadSnapshotView.as_view('lot_upload_snapshot'),
)
devices.add_url_rule('/device/add/', view_func=DeviceCreateView.as_view('device_add'))
devices.add_url_rule(
    '/lot/<string:lot_id>/device/add/',
    view_func=DeviceCreateView.as_view('lot_device_add'),
)
devices.add_url_rule('/tag/', view_func=TagListView.as_view('taglist'))
devices.add_url_rule('/tag/add/', view_func=TagAddView.as_view('tag_add'))
devices.add_url_rule(
    '/tag/unnamed/add/', view_func=TagAddUnnamedView.as_view('tag_unnamed_add')
)
devices.add_url_rule(
    '/tag/<string:id>/', view_func=TagDetailView.as_view('tag_details')
)
devices.add_url_rule(
    '/tag/devices/add/', view_func=TagLinkDeviceView.as_view('tag_devices_add')
)
devices.add_url_rule(
    '/tag/devices/<int:id>/del/',
    view_func=TagUnlinkDeviceView.as_view('tag_devices_del'),
)
devices.add_url_rule(
    '/export/<string:export_id>/', view_func=ExportsView.as_view('export')
)
