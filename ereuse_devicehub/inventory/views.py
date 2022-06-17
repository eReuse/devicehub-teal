import csv
import logging
from distutils.util import strtobool
from io import StringIO

import flask
import flask_weasyprint
from flask import Blueprint, g, make_response, request, url_for
from flask.views import View
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound

from ereuse_devicehub import messages
from ereuse_devicehub.db import db
from ereuse_devicehub.inventory.forms import (
    AdvancedSearchForm,
    AllocateForm,
    DataWipeForm,
    EditTransferForm,
    FilterForm,
    LotForm,
    NewActionForm,
    NewDeviceForm,
    NotesForm,
    TagDeviceForm,
    TradeDocumentForm,
    TradeForm,
    TransferForm,
    UploadSnapshotForm,
)
from ereuse_devicehub.labels.forms import PrintLabelsForm
from ereuse_devicehub.parser.models import SnapshotsLog
from ereuse_devicehub.resources.action.models import Trade
from ereuse_devicehub.resources.device.models import Computer, DataStorage, Device
from ereuse_devicehub.resources.documents.device_row import ActionRow, DeviceRow
from ereuse_devicehub.resources.enums import SnapshotSoftware
from ereuse_devicehub.resources.hash_reports import insert_hash
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.views import GenericMixin

devices = Blueprint('inventory', __name__, url_prefix='/inventory')

logger = logging.getLogger(__name__)


class DeviceListMixin(GenericMixin):
    template_name = 'inventory/device_list.html'

    def get_context(self, lot_id, only_unassigned=True):
        super().get_context()
        lots = self.context['lots']
        form_filter = FilterForm(lots, lot_id, only_unassigned=only_unassigned)
        devices = form_filter.search()
        lot = None
        form_transfer = ''
        form_delivery = ''
        form_receiver = ''

        if lot_id:
            lot = lots.filter(Lot.id == lot_id).one()
            if not lot.is_temporary and lot.transfer:
                form_transfer = EditTransferForm(lot_id=lot.id)
                form_delivery = NotesForm(lot_id=lot.id, type='Delivery')
                form_receiver = NotesForm(lot_id=lot.id, type='Receiver')

        form_new_action = NewActionForm(lot=lot_id)
        self.context.update(
            {
                'devices': devices,
                'form_tag_device': TagDeviceForm(),
                'form_new_action': form_new_action,
                'form_new_allocate': AllocateForm(lot=lot_id),
                'form_new_datawipe': DataWipeForm(lot=lot_id),
                'form_transfer': form_transfer,
                'form_delivery': form_delivery,
                'form_receiver': form_receiver,
                'form_filter': form_filter,
                'form_print_labels': PrintLabelsForm(),
                'lot': lot,
                'tags': self.get_user_tags(),
                'list_devices': self.get_selected_devices(form_new_action),
                'unassigned_devices': only_unassigned,
            }
        )

        return self.context

    def get_user_tags(self):
        return (
            Tag.query.filter(Tag.owner_id == current_user.id)
            .filter(Tag.device_id.is_(None))
            .order_by(Tag.id.asc())
        )

    def get_selected_devices(self, action_form):
        """Retrieve selected devices (when action form is submited)"""
        action_devices = action_form.devices.data
        if action_devices:
            return [int(x) for x in action_devices.split(",")]
        return []


class DeviceListView(DeviceListMixin):
    def dispatch_request(self, lot_id=None):
        only_unassigned = request.args.get(
            'only_unassigned', default=True, type=strtobool
        )
        self.get_context(lot_id, only_unassigned)
        return flask.render_template(self.template_name, **self.context)


class AdvancedSearchView(DeviceListMixin):
    methods = ['GET', 'POST']
    template_name = 'inventory/search.html'
    title = "Advanced Search"

    def dispatch_request(self):
        query = request.args.get('q', '')
        self.get_context(None)
        form = AdvancedSearchForm(q=query)
        self.context.update({'devices': form.devices, 'advanced_form': form})
        return flask.render_template(self.template_name, **self.context)


class DeviceDetailView(GenericMixin):
    decorators = [login_required]
    template_name = 'inventory/device_detail.html'

    def dispatch_request(self, id):
        self.get_context()
        device = (
            Device.query.filter(Device.owner_id == current_user.id)
            .filter(Device.devicehub_id == id)
            .one()
        )

        self.context.update(
            {
                'device': device,
                'page_title': 'Device {}'.format(device.devicehub_id),
            }
        )
        return flask.render_template(self.template_name, **self.context)


class LotCreateView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/lot.html'
    title = "Add a new lot"

    def dispatch_request(self):
        form = LotForm()
        if form.validate_on_submit():
            form.save()
            next_url = url_for('inventory.lotdevicelist', lot_id=form.id)
            return flask.redirect(next_url)

        self.get_context()
        self.context.update(
            {
                'form': form,
                'title': self.title,
            }
        )
        return flask.render_template(self.template_name, **self.context)


class LotUpdateView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/lot.html'
    title = "Edit a new lot"

    def dispatch_request(self, id):
        form = LotForm(id=id)
        if form.validate_on_submit():
            form.save()
            next_url = url_for('inventory.lotdevicelist', lot_id=id)
            return flask.redirect(next_url)

        self.get_context()
        self.context.update(
            {
                'form': form,
                'title': self.title,
            }
        )
        return flask.render_template(self.template_name, **self.context)


class LotDeleteView(View):
    methods = ['GET']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'

    def dispatch_request(self, id):
        form = LotForm(id=id)
        if form.instance.trade:
            msg = "Sorry, the lot cannot be deleted because have a trade action "
            messages.error(msg)
            next_url = url_for('inventory.lotdevicelist', lot_id=id)
            return flask.redirect(next_url)

        form.remove()
        next_url = url_for('inventory.devicelist')
        return flask.redirect(next_url)


class UploadSnapshotView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/upload_snapshot.html'

    def dispatch_request(self, lot_id=None):
        self.get_context()
        form = UploadSnapshotForm()
        self.context.update(
            {
                'page_title': 'Upload Snapshot',
                'form': form,
                'lot_id': lot_id,
            }
        )
        if form.validate_on_submit():
            snapshot, devices = form.save(commit=False)
            if lot_id:
                lots = self.context['lots']
                lot = lots.filter(Lot.id == lot_id).one()
                for dev in devices:
                    lot.devices.add(dev)
                db.session.add(lot)
            db.session.commit()

        return flask.render_template(self.template_name, **self.context)


class DeviceCreateView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/device_create.html'

    def dispatch_request(self, lot_id=None):
        self.get_context()
        form = NewDeviceForm()
        self.context.update(
            {
                'page_title': 'New Device',
                'form': form,
                'lot_id': lot_id,
            }
        )
        if form.validate_on_submit():
            snapshot = form.save(commit=False)
            next_url = url_for('inventory.devicelist')
            if lot_id:
                next_url = url_for('inventory.lotdevicelist', lot_id=lot_id)
                lots = self.context['lots']
                lot = lots.filter(Lot.id == lot_id).one()
                lot.devices.add(snapshot.device)
                db.session.add(lot)

            db.session.commit()
            messages.success('Device "{}" created successfully!'.format(form.type.data))
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, **self.context)


class TagLinkDeviceView(View):
    methods = ['POST']
    decorators = [login_required]
    # template_name = 'inventory/device_list.html'

    def dispatch_request(self):
        form = TagDeviceForm()
        if form.validate_on_submit():
            form.save()

            return flask.redirect(request.referrer)


class TagUnlinkDeviceView(GenericMixin):
    methods = ['POST', 'GET']
    decorators = [login_required]
    template_name = 'inventory/tag_unlink_device.html'

    def dispatch_request(self, id):
        self.get_context()
        form = TagDeviceForm(delete=True, device=id)
        if form.validate_on_submit():
            form.remove()

            next_url = url_for('inventory.devicelist')
            return flask.redirect(next_url)

        self.context.update(
            {
                'form': form,
                'referrer': request.referrer,
            }
        )

        return flask.render_template(self.template_name, **self.context)


class NewActionView(View):
    methods = ['POST']
    decorators = [login_required]
    form_class = NewActionForm

    def dispatch_request(self):
        self.form = self.form_class()
        next_url = self.get_next_url()

        if self.form.validate_on_submit():
            self.form.save()
            messages.success(
                'Action "{}" created successfully!'.format(self.form.type.data)
            )
            next_url = self.get_next_url()
            return flask.redirect(next_url)

        messages.error('Action {} error!'.format(self.form.type.data))
        return flask.redirect(next_url)

    def get_next_url(self):
        lot_id = self.form.lot.data

        if lot_id:
            return url_for('inventory.lotdevicelist', lot_id=lot_id)

        return url_for('inventory.devicelist')


class NewAllocateView(DeviceListMixin, NewActionView):
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

        messages.error('Action {} error!'.format(self.form.type.data))
        for k, v in self.form.errors.items():
            value = ';'.join(v)
            key = self.form[k].label.text
            messages.error('Action Error {key}: {value}!'.format(key=key, value=value))
        next_url = self.get_next_url()
        return flask.redirect(next_url)


class NewDataWipeView(DeviceListMixin, NewActionView):
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

        messages.error('Action {} error!'.format(self.form.type.data))
        next_url = self.get_next_url()
        return flask.redirect(next_url)


class NewTradeView(DeviceListMixin, NewActionView):
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

        messages.error('Action {} error!'.format(self.form.type.data))
        next_url = self.get_next_url()
        return flask.redirect(next_url)


class NewTradeDocumentView(View):
    methods = ['POST', 'GET']
    decorators = [login_required]
    template_name = 'inventory/trade_document.html'
    form_class = TradeDocumentForm
    title = "Add new document"

    def dispatch_request(self, lot_id):
        self.form = self.form_class(lot=lot_id)
        self.get_context()

        if self.form.validate_on_submit():
            self.form.save()
            messages.success('Document created successfully!')
            next_url = url_for('inventory.lotdevicelist', lot_id=lot_id)
            return flask.redirect(next_url)

        self.context.update({'form': self.form, 'title': self.title})
        return flask.render_template(self.template_name, **self.context)


class NewTransferView(GenericMixin):
    methods = ['POST', 'GET']
    template_name = 'inventory/new_transfer.html'
    form_class = TransferForm
    title = "Add new transfer"

    def dispatch_request(self, lot_id, type_id):
        self.form = self.form_class(lot_id=lot_id, type=type_id)
        self.get_context()

        if self.form.validate_on_submit():
            self.form.save()
            new_lot_id = lot_id
            if self.form.newlot.id:
                new_lot_id = "{}".format(self.form.newlot.id)
                Lot.query.filter(Lot.id == new_lot_id).one()
            messages.success('Transfer created successfully!')
            next_url = url_for('inventory.lotdevicelist', lot_id=str(new_lot_id))
            return flask.redirect(next_url)

        self.context.update({'form': self.form, 'title': self.title})
        return flask.render_template(self.template_name, **self.context)


class EditTransferView(GenericMixin):
    methods = ['POST']
    form_class = EditTransferForm

    def dispatch_request(self, lot_id):
        self.get_context()
        form = self.form_class(request.form, lot_id=lot_id)
        next_url = url_for('inventory.lotdevicelist', lot_id=lot_id)

        if form.validate_on_submit():
            form.save()
            messages.success('Transfer updated successfully!')
            return flask.redirect(next_url)

        messages.error('Transfer updated error!')
        for k, v in form.errors.items():
            value = ';'.join(v)
            key = form[k].label.text
            messages.error('Error {key}: {value}!'.format(key=key, value=value))
        return flask.redirect(next_url)


class ExportsView(View):
    methods = ['GET']
    decorators = [login_required]

    def dispatch_request(self, export_id):
        export_ids = {
            'metrics': self.metrics,
            'devices': self.devices_list,
            'certificates': self.erasure,
            'lots': self.lots_export,
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

    def lots_export(self):
        data = StringIO()
        cw = csv.writer(data, delimiter=';', lineterminator="\n", quotechar='"')

        cw.writerow(
            [
                'Lot Id',
                'Lot Name',
                'Lot Type',
                'Transfer Status',
                'Transfer Code',
                'Transfer Date',
                'Transfer Creation Date',
                'Transfer Update Date',
                'Transfer Description',
                'Devices Number',
                'Devices Snapshots',
                'Devices Placeholders',
                'Delivery Note Number',
                'Delivery Note Date',
                'Delivery Note Units',
                'Delivery Note Weight',
                'Receiver Note Number',
                'Receiver Note Date',
                'Receiver Note Units',
                'Receiver Note Weight',
            ]
        )

        for lot in Lot.query.filter_by(owner=g.user):
            delivery_note = lot.transfer and lot.transfer.delivery_note or ''
            receiver_note = lot.transfer and lot.transfer.receiver_note or ''
            wb_devs = 0
            placeholders = 0
            type_transfer = ''
            if lot.transfer:
                if lot.transfer.user_from == g.user:
                    type_transfer = 'Outgoing'
                if lot.transfer.user_to == g.user:
                    type_transfer = 'Incoming'
            else:
                type_transfer = 'Temporary'

            for dev in lot.devices:
                snapshots = [e for e in dev.actions if e.type == 'Snapshot']
                if not snapshots or snapshots[-1].software not in [
                    SnapshotSoftware.Workbench
                ]:
                    placeholders += 1
                elif snapshots[-1].software in [SnapshotSoftware.Workbench]:
                    wb_devs += 1

            row = [
                lot.id,
                lot.name,
                type_transfer,
                lot.transfer and (lot.transfer.closed and 'Closed' or 'Open') or '',
                lot.transfer and lot.transfer.code or '',
                lot.transfer and lot.transfer.date or '',
                lot.transfer and lot.transfer.created or '',
                lot.transfer and lot.transfer.updated or '',
                lot.transfer and lot.transfer.description or '',
                len(lot.devices),
                wb_devs,
                placeholders,
                delivery_note and delivery_note.number or '',
                delivery_note and delivery_note.date or '',
                delivery_note and delivery_note.units or '',
                delivery_note and delivery_note.weight or '',
                receiver_note and receiver_note.number or '',
                receiver_note and receiver_note.date or '',
                receiver_note and receiver_note.units or '',
                receiver_note and receiver_note.weight or '',
            ]
            cw.writerow(row)

        return self.response_csv(data, "lots_export.csv")


class SnapshotListView(GenericMixin):
    template_name = 'inventory/snapshots_list.html'

    def dispatch_request(self):
        self.get_context()
        self.context['page_title'] = "Snapshots Logs"
        self.context['snapshots_log'] = self.get_snapshots_log()

        return flask.render_template(self.template_name, **self.context)

    def get_snapshots_log(self):
        snapshots_log = SnapshotsLog.query.filter(
            SnapshotsLog.owner == g.user
        ).order_by(SnapshotsLog.created.desc())
        logs = {}
        for snap in snapshots_log:
            if snap.snapshot_uuid not in logs:
                logs[snap.snapshot_uuid] = {
                    'sid': snap.sid,
                    'snapshot_uuid': snap.snapshot_uuid,
                    'version': snap.version,
                    'device': snap.get_device(),
                    'status': snap.get_status(),
                    'severity': snap.severity,
                    'created': snap.created,
                }
                continue

            if snap.created > logs[snap.snapshot_uuid]['created']:
                logs[snap.snapshot_uuid]['created'] = snap.created

            if snap.severity > logs[snap.snapshot_uuid]['severity']:
                logs[snap.snapshot_uuid]['severity'] = snap.severity
                logs[snap.snapshot_uuid]['status'] = snap.get_status()

        result = sorted(logs.values(), key=lambda d: d['created'])
        result.reverse()

        return result


class SnapshotDetailView(GenericMixin):
    template_name = 'inventory/snapshot_detail.html'

    def dispatch_request(self, snapshot_uuid):
        self.snapshot_uuid = snapshot_uuid
        self.get_context()
        self.context['page_title'] = "Snapshot Detail"
        self.context['snapshots_log'] = self.get_snapshots_log()
        self.context['snapshot_uuid'] = snapshot_uuid
        self.context['snapshot_sid'] = ''
        if self.context['snapshots_log'].count():
            self.context['snapshot_sid'] = self.context['snapshots_log'][0].sid

        return flask.render_template(self.template_name, **self.context)

    def get_snapshots_log(self):
        return (
            SnapshotsLog.query.filter(SnapshotsLog.owner == g.user)
            .filter(SnapshotsLog.snapshot_uuid == self.snapshot_uuid)
            .order_by(SnapshotsLog.created.desc())
        )


class DeliveryNoteView(GenericMixin):
    methods = ['POST']
    form_class = NotesForm

    def dispatch_request(self, lot_id):
        self.get_context()
        form = self.form_class(request.form, lot_id=lot_id, type='Delivery')
        next_url = url_for('inventory.lotdevicelist', lot_id=lot_id)

        if form.validate_on_submit():
            form.save()
            messages.success('Delivery Note updated successfully!')
            return flask.redirect(next_url)

        messages.error('Delivery Note updated error!')
        for k, v in form.errors.items():
            value = ';'.join(v)
            key = form[k].label.text
            messages.error('Error {key}: {value}!'.format(key=key, value=value))
        return flask.redirect(next_url)


class ReceiverNoteView(GenericMixin):
    methods = ['POST']
    form_class = NotesForm

    def dispatch_request(self, lot_id):
        self.get_context()
        form = self.form_class(request.form, lot_id=lot_id, type='Receiver')
        next_url = url_for('inventory.lotdevicelist', lot_id=lot_id)

        if form.validate_on_submit():
            form.save()
            messages.success('Receiver Note updated successfully!')
            return flask.redirect(next_url)

        messages.error('Receiver Note updated error!')
        for k, v in form.errors.items():
            value = ';'.join(v)
            key = form[k].label.text
            messages.error('Error {key}: {value}!'.format(key=key, value=value))
        return flask.redirect(next_url)


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
    '/search/', view_func=AdvancedSearchView.as_view('advanced_search')
)
devices.add_url_rule(
    '/device/<string:id>/', view_func=DeviceDetailView.as_view('device_details')
)
devices.add_url_rule(
    '/lot/<string:lot_id>/device/', view_func=DeviceListView.as_view('lotdevicelist')
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
devices.add_url_rule('/snapshots/', view_func=SnapshotListView.as_view('snapshotslist'))
devices.add_url_rule(
    '/snapshots/<string:snapshot_uuid>/',
    view_func=SnapshotDetailView.as_view('snapshot_detail'),
)
devices.add_url_rule(
    '/lot/<string:lot_id>/transfer/<string:type_id>/',
    view_func=NewTransferView.as_view('new_transfer'),
)
devices.add_url_rule(
    '/lot/<string:lot_id>/transfer/',
    view_func=EditTransferView.as_view('edit_transfer'),
)
devices.add_url_rule(
    '/lot/<string:lot_id>/deliverynote/',
    view_func=DeliveryNoteView.as_view('delivery_note'),
)
devices.add_url_rule(
    '/lot/<string:lot_id>/receivernote/',
    view_func=ReceiverNoteView.as_view('receiver_note'),
)
