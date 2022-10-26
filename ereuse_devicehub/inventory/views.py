import copy
import csv
import logging
import os
from io import StringIO
from pathlib import Path

import flask
import flask_weasyprint
from flask import Blueprint
from flask import current_app as app
from flask import g, make_response, request, url_for
from flask.views import View
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound

from ereuse_devicehub import messages
from ereuse_devicehub.db import db
from ereuse_devicehub.inventory.forms import (
    AdvancedSearchForm,
    AllocateForm,
    BindingForm,
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
    UploadPlaceholderForm,
    UploadSnapshotForm,
)
from ereuse_devicehub.labels.forms import PrintLabelsForm
from ereuse_devicehub.parser.models import PlaceholdersLog, SnapshotsLog
from ereuse_devicehub.resources.action.models import EraseBasic, Trade
from ereuse_devicehub.resources.device.models import (
    Computer,
    DataStorage,
    Device,
    Placeholder,
)
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

    def get_context(self, lot_id=None, all_devices=False):
        super().get_context()

        lots = self.context['lots']
        form_filter = FilterForm(lots, lot_id, all_devices=all_devices)
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
                'all_devices': all_devices,
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


class ErasureListView(DeviceListMixin):
    template_name = 'inventory/erasure_list.html'

    def dispatch_request(self):
        self.get_context()
        self.get_devices()
        return flask.render_template(self.template_name, **self.context)

    def get_devices(self):
        erasure = EraseBasic.query.filter_by(author=g.user).order_by(
            EraseBasic.created.desc()
        )
        self.context['erasure'] = erasure


class DeviceListView(DeviceListMixin):
    def dispatch_request(self, lot_id=None):
        self.get_context(lot_id)
        return flask.render_template(self.template_name, **self.context)


class AllDeviceListView(DeviceListMixin):
    def dispatch_request(self):
        self.get_context(all_devices=True)
        return flask.render_template(self.template_name, **self.context)


class AdvancedSearchView(DeviceListMixin):
    methods = ['GET', 'POST']
    template_name = 'inventory/search.html'
    title = "Advanced Search"

    def dispatch_request(self):
        query = request.args.get('q', '')
        self.get_context()
        form = AdvancedSearchForm(q=query)
        self.context.update({'devices': form.devices, 'advanced_form': form})
        return flask.render_template(self.template_name, **self.context)


class DeviceDetailView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/device_detail.html'

    def dispatch_request(self, id):
        self.get_context()
        device = (
            Device.query.filter(Device.owner_id == current_user.id)
            .filter(Device.devicehub_id == id)
            .one()
        )

        form_tags = TagDeviceForm(dhid=id)
        placeholder = device.binding or device.placeholder
        if not placeholder:
            return NotFound()

        self.context.update(
            {
                'device': device,
                'placeholder': placeholder,
                'page_title': 'Device {}'.format(device.devicehub_id),
                'form_tag_device': form_tags,
            }
        )

        return flask.render_template(self.template_name, **self.context)


class BindingSearchView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/binding_search.html'

    def dispatch_request(self, dhid):
        self.get_context()
        device = (
            Device.query.filter(Device.owner_id == current_user.id)
            .filter(Device.devicehub_id == dhid)
            .one()
        )

        form_binding = BindingForm(device=device)

        self.context.update(
            {
                'page_title': 'Search a Device for to do a binding from {}'.format(
                    device.devicehub_id
                ),
                'form_binding': form_binding,
                'device': device,
            }
        )

        if form_binding.validate_on_submit():
            next_url = url_for(
                'inventory.binding',
                dhid=dhid,
                phid=form_binding.placeholder.phid,
            )
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, **self.context)


class BindingView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/binding.html'

    def dispatch_request(self, dhid, phid):
        self.phid = phid
        self.dhid = dhid
        self.next_url = url_for('inventory.device_details', id=dhid)
        self.get_context()
        self.get_objects()
        if self.check_errors():
            return flask.redirect(self.next_url)

        if request.method == 'POST':
            return self.post()

        self.context.update(
            {
                'new_placeholder': self.new_placeholder,
                'old_placeholder': self.old_placeholder,
                'page_title': 'Binding confirm',
                'actions': list(self.old_device.actions)
                + list(self.new_device.actions),
                'tags': list(self.old_device.tags) + list(self.new_device.tags),
                'dhid': self.dhid,
            }
        )

        return flask.render_template(self.template_name, **self.context)

    def check_errors(self):
        if not self.new_placeholder:
            messages.error('Device Phid: "{}" not exist!'.format(self.phid))
            return True

        if self.old_device.placeholder.status != 'Snapshot':
            messages.error(
                'Device Dhid: "{}" is not a Snapshot device!'.format(self.dhid)
            )
            return True

        if self.new_placeholder.status == 'Twin':
            messages.error('Device Phid: "{}" is a Twin device!'.format(self.phid))
            return True

        if self.new_placeholder.status == self.old_placeholder.status:
            txt = 'Device Phid: "{}" and device Dhid: "{}" have the same status, "{}"!'.format(
                self.phid, self.dhid, self.new_placeholder.status
            )
            messages.error(txt)
            return True

    def get_objects(self):
        self.old_device = (
            Device.query.filter(Device.owner_id == g.user.id)
            .filter(Device.devicehub_id == self.dhid)
            .one()
        )
        self.new_placeholder = (
            Placeholder.query.filter(Placeholder.owner_id == g.user.id)
            .filter(Placeholder.phid == self.phid)
            .first()
        )

        if not self.new_placeholder:
            return

        if self.old_device.placeholder.status == 'Snapshot':
            self.new_device = self.new_placeholder.device
            self.old_placeholder = self.old_device.placeholder
        elif self.old_device.placeholder.status == 'Placeholder':
            self.new_device = self.old_device
            self.old_placeholder = self.new_placeholder
            self.old_device = self.old_placeholder.device
            self.new_placeholder = self.new_device.placeholder

        self.abstract_device = self.old_placeholder.binding
        self.real_dhid = self.new_device.devicehub_id
        self.real_phid = self.new_placeholder.phid
        self.abstract_dhid = self.old_device.devicehub_id
        self.abstract_phid = self.old_placeholder.phid
        if self.old_placeholder.kangaroo:
            self.new_placeholder.kangaroo = True

        # to do a backup of abstract_dhid and abstract_phid in
        # workbench device
        if self.abstract_device:
            self.abstract_device.dhid_bk = self.abstract_dhid
            self.abstract_device.phid_bk = self.abstract_phid

    def post(self):
        for plog in PlaceholdersLog.query.filter_by(
            placeholder_id=self.old_placeholder.id
        ):
            db.session.delete(plog)

        for ac in self.old_device.actions:
            ac.devices.add(self.new_device)
            ac.devices.remove(self.old_device)
            for act in ac.actions_device:
                if act.device == self.old_device:
                    db.session.delete(act)

        for tag in list(self.old_device.tags):
            tag.device = self.new_device

        db.session.delete(self.old_device)
        self.abstract_device.binding = self.new_placeholder
        db.session.commit()

        next_url = url_for('inventory.device_details', id=self.real_dhid)
        txt = 'Device placeholder with PHID: {} and DHID: {} bind successfully with '
        txt += 'device snapshot PHID: {} DHID: {}.'
        messages.success(
            txt.format(
                self.real_phid, self.real_dhid, self.abstract_phid, self.abstract_dhid
            )
        )
        return flask.redirect(next_url)


class UnBindingView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/unbinding.html'

    def dispatch_request(self, phid):
        placeholder = (
            Placeholder.query.filter(Placeholder.owner_id == g.user.id)
            .filter(Placeholder.phid == phid)
            .one()
        )
        if not placeholder.binding or placeholder.status != 'Twin':
            next_url = url_for(
                'inventory.device_details', id=placeholder.device.devicehub_id
            )
            return flask.redirect(next_url)

        if placeholder.status != 'Twin':
            dhid = placeholder.device.devicehub_id
            next_url = url_for('inventory.device_details', id=dhid)
            messages.error('Device Dhid: "{}" not is a Twin device!'.format(dhid))
            return flask.redirect(next_url)

        self.get_context()

        if request.method == 'POST':
            dhid = placeholder.device.devicehub_id
            self.clone_device(placeholder.binding)
            next_url = url_for('inventory.device_details', id=dhid)
            messages.success(
                'Device with PHID:"{}" and DHID: {} unbind successfully!'.format(
                    phid, dhid
                )
            )
            return flask.redirect(next_url)

        self.context.update(
            {
                'placeholder': placeholder,
                'page_title': 'Unbinding confirm',
            }
        )

        return flask.render_template(self.template_name, **self.context)

    def clone_device(self, device):
        if device.binding and device.binding.is_abstract:
            return

        kangaroo = False
        if device.binding:
            kangaroo = device.binding.kangaroo
            device.binding.kangaroo = False

        dict_device = copy.copy(device.__dict__)
        dict_device.pop('_sa_instance_state')
        dict_device.pop('id', None)
        dict_device.pop('devicehub_id', None)
        dict_device.pop('actions_multiple', None)
        dict_device.pop('actions_one', None)
        dict_device.pop('components', None)
        dict_device.pop('tags', None)
        dict_device.pop('system_uuid', None)
        dict_device.pop('binding', None)
        dict_device.pop('placeholder', None)
        new_device = device.__class__(**dict_device)
        db.session.add(new_device)

        if hasattr(device, 'components'):
            for c in device.components:
                if c.binding:
                    c.binding.device.parent = new_device
                else:
                    new_c = self.clone_device(c)
                    new_c.parent = new_device

        placeholder = Placeholder(
            device=new_device, binding=device, is_abstract=True, kangaroo=kangaroo
        )

        if (
            device.dhid_bk
            and not Device.query.filter_by(devicehub_id=device.dhid_bk).first()
        ):
            new_device.devicehub_id = device.dhid_bk
        if (
            device.phid_bk
            and not Placeholder.query.filter_by(phid=device.phid_bk).first()
        ):
            placeholder.phid = device.phid_bk

        db.session.add(placeholder)
        db.session.commit()

        return new_device


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
            form.save(commit=False)
            next_url = url_for('inventory.devicelist')
            if lot_id:
                next_url = url_for('inventory.lotdevicelist', lot_id=lot_id)
                if form.objs:
                    lots = self.context['lots']
                    lot = lots.filter(Lot.id == lot_id).one()
                    lot.devices = lot.devices.union(form.objs)
                else:
                    messages.error('Sorry, the device could not be created')

            db.session.commit()

            amount = form.amount.data
            tpy = form.type.data
            txt = f'{amount} placeholders Device "{tpy}" created successfully.'
            placeholder = (
                Placeholder.query.filter(Placeholder.owner == g.user)
                .order_by(Placeholder.id.desc())
                .first()
            )
            if amount == 1 and placeholder:
                phid = placeholder.phid
                dhid = placeholder.device.devicehub_id
                txt = f'Device "{tpy}" placeholder with PHID {phid} and DHID {dhid} '
                txt += 'created successfully'
            messages.success(txt)
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, **self.context)


class DeviceEditView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/device_create.html'

    def dispatch_request(self, id):
        self.get_context()
        device = (
            Device.query.filter(Device.owner_id == current_user.id)
            .filter(Device.devicehub_id == id)
            .one()
        )
        form = NewDeviceForm(_obj=device)
        self.context.update(
            {
                'page_title': 'Edit Device',
                'form': form,
            }
        )
        if form.validate_on_submit():
            next_url = url_for('inventory.device_details', id=id)
            form.save(commit=True)
            messages.success('Device "{}" edited successfully!'.format(form.type.data))
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, **self.context)


class TagLinkDeviceView(View):
    methods = ['POST']
    decorators = [login_required]

    def dispatch_request(self, dhid):
        form = TagDeviceForm(dhid=dhid)
        if form.validate_on_submit():
            tag = form.tag.data
            form.save()

            next_url = url_for('inventory.device_details', id=dhid)
            messages.success('Tag {} was linked successfully!'.format(tag))
            return flask.redirect(next_url)


class TagUnlinkDeviceView(GenericMixin):
    methods = ['POST', 'GET']
    decorators = [login_required]
    template_name = 'inventory/tag_unlink_device.html'

    def dispatch_request(self, dhid):
        self.get_context()
        form = TagDeviceForm(delete=True, dhid=dhid)
        if form.validate_on_submit():
            form.remove()

            next_url = url_for('inventory.device_details', id=dhid)
            messages.success('Tag {} was unlinked successfully!'.format(form.tag.data))
            return flask.redirect(next_url)

        self.context.update(
            {
                'form': form,
                'dhid': dhid,
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

        if url_for('inventory.alldevicelist') in (request.referrer or ''):
            return url_for('inventory.alldevicelist')
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


class NewTradeDocumentView(GenericMixin):
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

    def dispatch_request(self, type_id, lot_id=None):
        self.form = self.form_class(lot_id=lot_id, type=type_id)
        self.get_context()
        referrer = request.referrer or url_for('inventory.devicelist')
        self.context.update({'referrer': referrer})

        if self.form.validate_on_submit():
            self.form.save()
            new_lot_id = lot_id
            if self.form.newlot.id:
                new_lot_id = "{}".format(self.form.newlot.id)
                Lot.query.filter(Lot.id == new_lot_id).one()
            messages.success('Transfer created successfully!')
            next_url = url_for('inventory.lotdevicelist', lot_id=str(new_lot_id))
            return flask.redirect(next_url)

        self.context.update(
            {
                'form': self.form,
                'title': self.title,
            }
        )
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
            'actions_erasures': self.actions_erasures,
            'certificates': self.erasure,
            'lots': self.lots_export,
            'devices_lots': self.devices_lots_export,
            'snapshot': self.snapshot,
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
        cw = csv.writer(
            data,
            delimiter=';',
            lineterminator="\n",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
        )
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
        cw = csv.writer(
            data,
            delimiter=';',
            lineterminator="\n",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
        )
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

    def actions_erasures(self):
        data = StringIO()
        cw = csv.writer(
            data,
            delimiter=';',
            lineterminator="\n",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
        )

        cw.writerow(
            [
                'Data Storage Serial',
                'DHID',
                'Snapshot ID',
                'Type of Erasure',
                'PHID Erasure Host',
                'Result',
                'Time',
            ]
        )

        args = request.args.get('ids')
        ids = args.split(',') if args else []
        ids = [id.strip() for id in ids]

        query = EraseBasic.query.filter_by(author=g.user)
        query = query.filter(EraseBasic.id.in_(ids))
        query = query.order_by(EraseBasic.created.desc())

        for ac in query:
            row = [
                ac.device.serial_number.upper(),
                ac.device.dhid,
                ac.snapshot.uuid,
                ac.type,
                ac.get_phid(),
                ac.severity,
                ac.created.strftime('%Y-%m-%d %H:%M:%S'),
            ]
            cw.writerow(row)

        return self.response_csv(data, "Erasures.csv")

    def build_erasure_certificate(self):
        erasures = []
        for device in self.find_devices():
            if device.placeholder and device.placeholder.binding:
                device = device.placeholder.binding
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
        cw = csv.writer(
            data,
            delimiter=';',
            lineterminator="\n",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
        )

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
                lot.type_transfer(),
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

    def devices_lots_export(self):
        data = StringIO()
        cw = csv.writer(
            data,
            delimiter=';',
            lineterminator="\n",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
        )
        head = [
            'DHID',
            'Lot Id',
            'Lot Name',
            'Lot Type',
            'Transfer Status',
            'Transfer Code',
            'Transfer Date',
            'Transfer Creation Date',
            'Transfer Update Date',
        ]
        cw.writerow(head)

        for dev in self.find_devices():
            for lot in dev.lots:
                row = [
                    dev.devicehub_id,
                    lot.id,
                    lot.name,
                    lot.type_transfer(),
                    lot.transfer and (lot.transfer.closed and 'Closed' or 'Open') or '',
                    lot.transfer and lot.transfer.code or '',
                    lot.transfer and lot.transfer.date or '',
                    lot.transfer and lot.transfer.created or '',
                    lot.transfer and lot.transfer.updated or '',
                ]
                cw.writerow(row)

        return self.response_csv(
            data, "Devices_Incoming_and_Outgoing_Lots_Spreadsheet.csv"
        )

    def snapshot(self):
        uuid = request.args.get('id')
        if not uuid:
            messages.error('Snapshot not exist!')
            return flask.redirect(request.referrer)

        user = g.user.email
        name_file = f"*_{user}_{uuid}.json"
        tmp_snapshots = app.config['TMP_SNAPSHOTS']
        path_dir_base = os.path.join(tmp_snapshots, user)

        for _file in Path(path_dir_base).glob(name_file):
            with open(_file) as file_snapshot:
                snapshot = file_snapshot.read()
            data = StringIO()
            data.write(snapshot)
            bfile = data.getvalue().encode('utf-8')
            output = make_response(bfile)
            output.headers['Content-Disposition'] = 'attachment; filename={}'.format(
                name_file
            )
            output.headers['Content-type'] = 'text/json'
            return output

        messages.error('Snapshot not exist!')
        return flask.redirect(request.referrer)


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
            try:
                system_uuid = snap.snapshot.device.system_uuid or ''
            except AttributeError:
                system_uuid = ''

            if snap.snapshot_uuid not in logs:
                logs[snap.snapshot_uuid] = {
                    'sid': snap.sid,
                    'snapshot_uuid': snap.snapshot_uuid,
                    'version': snap.version,
                    'device': snap.get_device(),
                    'system_uuid': system_uuid,
                    'status': snap.get_status(),
                    'severity': snap.severity,
                    'created': snap.created,
                    'type_device': snap.get_type_device(),
                    'original_dhid': snap.get_original_dhid(),
                    'new_device': snap.get_new_device(),
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


class UploadPlaceholderView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'inventory/upload_placeholder.html'

    def dispatch_request(self, lot_id=None):
        self.get_context()
        form = UploadPlaceholderForm()
        self.context.update(
            {
                'page_title': 'Upload Placeholder',
                'form': form,
                'lot_id': lot_id,
            }
        )
        if form.validate_on_submit():
            snapshots = form.save(commit=False)
            if lot_id:
                lots = self.context['lots']
                lot = lots.filter(Lot.id == lot_id).one()
                for device, p in snapshots:
                    lot.devices.add(device)
                db.session.add(lot)
            db.session.commit()
            dev_new = form.dev_new
            dev_update = form.dev_update
            total = dev_new + dev_update
            txt = 'Placeholders uploaded successfully!'

            if dev_update == 0:
                txt = f'A total of {total} Placeholders have been successfully'
                txt += ' uploaded. All of them have been new registrations in'
                txt += ' the system.'

            if dev_new == 0:
                txt = f'A total of {total} Placeholders have been successfully'
                txt += ' uploaded. All of them are updates.'

            if dev_new and dev_update:
                txt = f'A total of {total} Placeholders have been successfully'
                txt += f' uploaded. Among these {dev_new} are registered for '
                txt += ' the first time in the system and another'
                txt += f' {dev_update} have been updated.'

            messages.success(txt)

        return flask.render_template(self.template_name, **self.context)


class PlaceholderLogListView(GenericMixin):
    template_name = 'inventory/placeholder_log_list.html'

    def dispatch_request(self):
        self.get_context()
        self.context['page_title'] = "Placeholder Logs"
        self.context['placeholders_log'] = self.get_placeholders_log()

        return flask.render_template(self.template_name, **self.context)

    def get_placeholders_log(self):
        placeholder_log = PlaceholdersLog.query.filter(
            PlaceholdersLog.owner == g.user
        ).order_by(PlaceholdersLog.created.desc())

        return placeholder_log


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
    '/all/device/', view_func=AllDeviceListView.as_view('alldevicelist')
)
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
    '/device/edit/<string:id>/', view_func=DeviceEditView.as_view('device_edit')
)
devices.add_url_rule(
    '/tag/devices/<string:dhid>/add/',
    view_func=TagLinkDeviceView.as_view('tag_devices_add'),
)
devices.add_url_rule(
    '/tag/devices/<string:dhid>/del/',
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
    view_func=NewTransferView.as_view('lot_new_transfer'),
)
devices.add_url_rule(
    '/lot/transfer/<string:type_id>/',
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
devices.add_url_rule(
    '/upload-placeholder/',
    view_func=UploadPlaceholderView.as_view('upload_placeholder'),
)
devices.add_url_rule(
    '/lot/<string:lot_id>/upload-placeholder/',
    view_func=UploadPlaceholderView.as_view('lot_upload_placeholder'),
)
devices.add_url_rule(
    '/placeholder-logs/', view_func=PlaceholderLogListView.as_view('placeholder_logs')
)
devices.add_url_rule(
    '/binding/<string:dhid>/<string:phid>/', view_func=BindingView.as_view('binding')
)
devices.add_url_rule(
    '/unbinding/<string:phid>/', view_func=UnBindingView.as_view('unbinding')
)
devices.add_url_rule(
    '/device/<string:dhid>/binding/',
    view_func=BindingSearchView.as_view('binding_search'),
)
devices.add_url_rule(
    '/device/erasure/', view_func=ErasureListView.as_view('device_erasure_list')
)
