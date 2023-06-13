import copy
import csv
import datetime
import logging
import os
import uuid
from io import StringIO
from pathlib import Path

import flask
import flask_weasyprint
from flask import Blueprint
from flask import current_app as app
from flask import g, make_response, request, url_for
from flask.views import View
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.exceptions import NotFound

from ereuse_devicehub import messages
from ereuse_devicehub.db import db
from ereuse_devicehub.inventory.forms import (
    AdvancedSearchForm,
    AllocateForm,
    BindingForm,
    CustomerDetailsForm,
    DataWipeForm,
    DeviceDocumentForm,
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
    UserTrustsForm,
)
from ereuse_devicehub.labels.forms import PrintLabelsForm
from ereuse_devicehub.parser.models import PlaceholdersLog, SnapshotsLog
from ereuse_devicehub.resources.action.models import EraseBasic, Trade
from ereuse_devicehub.resources.device.models import (
    Computer,
    DataStorage,
    Device,
    Mobile,
    Placeholder,
)
from ereuse_devicehub.resources.documents.device_row import ActionRow, DeviceRow
from ereuse_devicehub.resources.enums import SnapshotSoftware
from ereuse_devicehub.resources.hash_reports import insert_hash
from ereuse_devicehub.resources.lot.models import Lot, ShareLot
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.views import GenericMixin

devices = Blueprint('inventory', __name__, url_prefix='/inventory')

logger = logging.getLogger(__name__)


PER_PAGE = 20


class DeviceListMixin(GenericMixin):
    template_name = 'inventory/device_list.html'

    def get_context(self, lot_id=None, all_devices=False):
        super().get_context()

        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', PER_PAGE))
        filter = request.args.get('filter', "All+Computers")

        lot = None

        share_lots = self.context['share_lots']
        share_lot = share_lots.filter_by(lot_id=lot_id).first()
        if share_lot:
            lot = share_lot.lot

        lots = self.context['lots']
        form_filter = FilterForm(lots, lot, lot_id, all_devices=all_devices)
        devices = form_filter.search().paginate(page=page, per_page=per_page)
        devices.first = per_page * devices.page - per_page + 1
        devices.last = len(devices.items) + devices.first - 1

        form_transfer = ''
        form_delivery = ''
        form_receiver = ''
        form_customer_details = ''

        if lot_id and not lot:
            lot = lots.filter(Lot.id == lot_id).one()
            if not lot.is_temporary and lot.transfer:
                form_transfer = EditTransferForm(lot_id=lot.id)
                form_delivery = NotesForm(lot_id=lot.id, type='Delivery')
                form_receiver = NotesForm(lot_id=lot.id, type='Receiver')
                form_customer_details = CustomerDetailsForm(lot_id=lot.id)

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
                'form_customer_details': form_customer_details,
                'form_filter': form_filter,
                'form_print_labels': PrintLabelsForm(),
                'lot': lot,
                'tags': self.get_user_tags(),
                'list_devices': self.get_selected_devices(form_new_action),
                'all_devices': all_devices,
                'filter': filter,
                'share_lots': share_lots,
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

    def dispatch_request(self, orphans=0):
        self.get_context()
        self.get_devices(orphans)
        return flask.render_template(self.template_name, **self.context)

    def get_devices(self, orphans):
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', PER_PAGE))

        erasure = EraseBasic.query.filter_by(author=g.user).order_by(
            EraseBasic.created.desc()
        )
        if orphans:
            schema = app.config.get('SCHEMA')
            _user = g.user.id
            sql = f"""
                select action.id from {schema}.action as action
                    inner join {schema}.erase_basic as erase
                        on action.id=erase.id
                    inner join {schema}.device as device
                        on device.id=action.parent_id
                    inner join {schema}.placeholder as placeholder
                        on placeholder.binding_id=device.id
                    where (action.parent_id is null or placeholder.kangaroo=true)
                    and action.author_id='{_user}'
            """
            ids = (e[0] for e in db.session.execute(sql))
            erasure = (
                EraseBasic.query.filter(EraseBasic.id.in_(ids))
                .filter_by(author=g.user)
                .order_by(EraseBasic.created.desc())
            )
            self.context['orphans'] = True

        erasure = erasure.paginate(page=page, per_page=per_page)
        erasure.first = per_page * erasure.page - per_page + 1
        erasure.last = len(erasure.items) + erasure.first - 1
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
        shared = ShareLot.query.filter_by(lot=form.instance).first()
        if form.instance.trade or shared:
            msg = "Sorry, the lot cannot be deleted because this lot is share"
            messages.error(msg)
            next_url = url_for('inventory.lotdevicelist', lot_id=id)
            return flask.redirect(next_url)

        form.remove()
        next_url = url_for('inventory.devicelist')
        return flask.redirect(next_url)


class DocumentDeleteView(View):
    methods = ['GET']
    decorators = [login_required]
    template_name = 'inventory/device_list.html'
    form_class = TradeDocumentForm

    def dispatch_request(self, lot_id, doc_id):
        next_url = url_for('inventory.lotdevicelist', lot_id=lot_id)
        form = self.form_class(lot=lot_id, document=doc_id)
        try:
            form.remove()
        except Exception as err:
            msg = "{}".format(err)
            messages.error(msg)
            return flask.redirect(next_url)

        msg = "Document removed successfully."
        messages.success(msg)
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


class NewDeviceDocumentView(GenericMixin):
    methods = ['POST', 'GET']
    decorators = [login_required]
    template_name = 'inventory/device_document.html'
    form_class = DeviceDocumentForm
    title = "Add new document"

    def dispatch_request(self, dhid):
        self.form = self.form_class(dhid=dhid)
        self.get_context()

        if self.form.validate_on_submit():
            self.form.save()
            messages.success('Document created successfully!')
            next_url = url_for('inventory.device_details', id=dhid)
            return flask.redirect(next_url)

        self.context.update({'form': self.form, 'title': self.title})
        return flask.render_template(self.template_name, **self.context)


class EditDeviceDocumentView(GenericMixin):
    decorators = [login_required]
    methods = ['POST', 'GET']
    template_name = 'inventory/device_document.html'
    form_class = DeviceDocumentForm
    title = "Edit document"

    def dispatch_request(self, dhid, doc_id):
        self.form = self.form_class(dhid=dhid, document=doc_id)
        self.get_context()

        if self.form.validate_on_submit():
            self.form.save()
            messages.success('Edit document successfully!')
            next_url = url_for('inventory.device_details', id=dhid)
            return flask.redirect(next_url)

        self.context.update({'form': self.form, 'title': self.title})
        return flask.render_template(self.template_name, **self.context)


class DeviceDocumentDeleteView(View):
    methods = ['GET']
    decorators = [login_required]
    template_name = 'inventory/device_detail.html'
    form_class = DeviceDocumentForm

    def dispatch_request(self, dhid, doc_id):
        self.form = self.form_class(dhid=dhid, document=doc_id)
        next_url = url_for('inventory.device_details', id=dhid)
        try:
            self.form.remove()
        except Exception as err:
            msg = "{}".format(err)
            messages.error(msg)
            return flask.redirect(next_url)

        msg = "Document removed successfully."
        messages.success(msg)
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


class EditTransferDocumentView(GenericMixin):
    decorators = [login_required]
    methods = ['POST', 'GET']
    template_name = 'inventory/trade_document.html'
    form_class = TradeDocumentForm
    title = "Edit document"

    def dispatch_request(self, lot_id, doc_id):
        self.form = self.form_class(lot=lot_id, document=doc_id)
        self.get_context()

        if self.form.validate_on_submit():
            self.form.save()
            messages.success('Edit document successfully!')
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


class OpenTransferView(GenericMixin):
    methods = ['GET']

    def dispatch_request(self, lot_id=None):
        lot = Lot.query.filter_by(id=lot_id).one()
        next_url = url_for('inventory.lotdevicelist', lot_id=str(lot_id))

        if hasattr(lot, 'transfer'):
            lot.transfer.date = None
            db.session.commit()
            messages.success('Transfer was reopen successfully!')

        return flask.redirect(next_url)


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
            'obada_standard': self.obada_standard_export,
            'snapshot': self.snapshot,
        }

        if export_id not in export_ids:
            return NotFound()
        return export_ids[export_id]()

    def find_devices(self):
        sql = """
            select lot_device.device_id as id from {schema}.share_lot as share
                inner join {schema}.lot_device as lot_device
                    on share.lot_id=lot_device.lot_id
                where share.user_to_id='{user_id}'
        """.format(
            schema=app.config.get('SCHEMA'), user_id=g.user.id
        )

        shared = (x[0] for x in db.session.execute(sql))

        args = request.args.get('ids')
        ids = args.split(',') if args else []
        query = Device.query.filter(or_(Device.owner == g.user, Device.id.in_(shared)))
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

    def obada_standard_export(self):
        """Get device information for Obada Standard."""
        data = StringIO()
        cw = csv.writer(
            data,
            delimiter=',',
            lineterminator="\n",
            quotechar='',
            quoting=csv.QUOTE_NONE,
        )

        cw.writerow(['Manufacturer', 'Model', 'Serial Number'])

        for device in self.find_devices():
            if device.placeholder:
                if not device.placeholder.binding:
                    continue
                device = device.placeholder.binding

            d = [
                device.manufacturer,
                device.model,
                device.serial_number,
            ]
            cw.writerow(d)

        return self.response_csv(data, "obada_standard.csv")

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
                ac.snapshot.uuid if ac.snapshot else '',
                ac.type,
                ac.parent.phid() if ac.parent else '',
                ac.severity,
                ac.created.strftime('%Y-%m-%d %H:%M:%S'),
            ]
            cw.writerow(row)

        return self.response_csv(data, "Erasures.csv")

    def get_datastorages(self):
        erasures = []
        for device in self.find_devices():
            if device.placeholder and device.placeholder.binding:
                device = device.placeholder.binding
            if isinstance(device, Computer):
                for ac in device.last_erase_action:
                    erasures.append(ac)
            elif isinstance(device, DataStorage):
                ac = device.last_erase_action
                if ac:
                    erasures.append(ac)
            elif isinstance(device, Mobile):
                ac = device.last_erase_action
                if ac:
                    erasures.append(ac)
        return erasures

    def get_costum_details(self, erasures):
        my_data = None
        customer_details = None
        lot = None

        if hasattr(g.user, 'sanitization_entity'):
            my_data = g.user.sanitization_entity

        customer_details = self.get_customer_details_from_request()

        if not erasures or customer_details:
            return my_data, customer_details

        lots = {erasures[0].device.get_last_incoming_lot()}
        for e in erasures[1:]:
            lots.add(e.device.get_last_incoming_lot())

        if len(lots) != 1:
            return my_data, customer_details

        lot = lots.pop()
        try:
            customer_details = lot.transfer.customer_details
        except Exception:
            pass

        return my_data, customer_details

    def get_customer_details_from_request(self):
        try:
            if len(request.referrer.split('/lot/')) < 2:
                return

            lot_id = request.referrer.split('/lot/')[-1].split('/')[0]
            lot = Lot.query.filter_by(owner=g.user).filter_by(id=lot_id).first()
            return lot.transfer.customer_details
        except Exception:
            pass

    def get_server_erasure_hosts(self, erasures):
        erasures_host = []
        erasures_mobile = []
        erasures_on_server = []
        for erase in erasures:
            try:
                if isinstance(erase.device, Mobile):
                    erasures_mobile.append(erase.device)
                    continue
                if erase.parent.binding.kangaroo:
                    erasures_host.append(erase.parent)
                    erasures_on_server.append(erase)
            except Exception:
                pass
        return erasures_host, erasures_on_server, erasures_mobile

    def build_erasure_certificate(self):
        erasures = self.get_datastorages()
        software = 'USODY DRIVE ERASURE'
        if erasures and erasures[0].snapshot:
            software += ' {}'.format(
                erasures[0].snapshot.version,
            )

        my_data, customer_details = self.get_costum_details(erasures)

        a, b, c = self.get_server_erasure_hosts(erasures)
        erasures_host, erasures_on_server, erasures_mobile = a, b, c
        erasures_host = set(erasures_host)
        erasures_mobile = set(erasures_mobile)

        result_success = 0
        result_failed = 0
        for e in erasures:
            result = e.severity.get_public_name()
            if "Failed" == result:
                result_failed += 1
            if "Success" == result:
                result_success += 1

        erasures = sorted(erasures, key=lambda x: x.end_time)
        erasures_on_server = sorted(erasures_on_server, key=lambda x: x.end_time)
        erasures_normal = list(set(erasures) - set(erasures_on_server))
        erasures_normal = sorted(erasures_normal, key=lambda x: x.end_time)
        n_computers = len({x.parent for x in erasures if x.parent} - erasures_host)
        n_mobiles = len(erasures_mobile)

        params = {
            'title': 'Device Sanitization',
            'erasures': tuple(erasures),
            'url_pdf': '',
            'date_report': '{:%c}'.format(datetime.datetime.now()),
            'uuid_report': '{}'.format(uuid.uuid4()),
            'software': software,
            'my_data': my_data,
            'n_computers': n_computers,
            'n_mobiles': n_mobiles,
            'result_success': result_success,
            'result_failed': result_failed,
            'customer_details': customer_details,
            'erasure_hosts': erasures_host,
            'erasure_mobiles': erasures_mobile,
            'erasures_normal': erasures_normal,
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
                'Customer Company Name',
                'Customer Location',
            ]
        )

        all_lots = set(Lot.query.filter_by(owner=g.user).all())
        share_lots = [s.lot for s in ShareLot.query.filter_by(user_to=g.user)]
        all_lots = all_lots.union(share_lots)
        for lot in all_lots:
            delivery_note = lot.transfer and lot.transfer.delivery_note or ''
            receiver_note = lot.transfer and lot.transfer.receiver_note or ''
            customer = lot.transfer and lot.transfer.customer_details or ''
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

            type_lot = lot.type_transfer()
            if lot in share_lots:
                type_lot = "Shared"
            row = [
                lot.id,
                lot.name,
                type_lot,
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
                customer and customer.company_name or '',
                customer and customer.location or '',
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
                type_lot = lot.type_transfer()
                if lot.is_shared:
                    type_lot = "Shared"
                row = [
                    dev.devicehub_id,
                    lot.id,
                    lot.name,
                    type_lot,
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
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', PER_PAGE))

        snapshots_log = SnapshotsLog.query.filter(
            SnapshotsLog.owner == g.user
        ).order_by(SnapshotsLog.created.desc())

        snapshots_log = snapshots_log.paginate(page=page, per_page=per_page)
        snapshots_log.first = per_page * snapshots_log.page - per_page + 1
        snapshots_log.last = len(snapshots_log.items) + snapshots_log.first - 1
        return snapshots_log


class SnapshotDetailView(GenericMixin):
    template_name = 'inventory/snapshot_detail.html'
    methods = ['GET', 'POST']
    form_class = UserTrustsForm

    def dispatch_request(self, snapshot_uuid):
        self.snapshot_uuid = snapshot_uuid
        form = self.form_class(snapshot_uuid)
        self.get_context()
        self.context['page_title'] = "Snapshot Detail"
        self.context['snapshots_log'] = self.get_snapshots_log()
        self.context['snapshot_uuid'] = snapshot_uuid
        self.context['snapshot_sid'] = ''
        if self.context['snapshots_log'].count():
            self.context['snapshot_sid'] = self.context['snapshots_log'][0].sid
        self.context['form'] = form

        if form.validate_on_submit():
            form.save()

        return flask.render_template(self.template_name, **self.context)

    def get_snapshots_log(self):
        return (
            SnapshotsLog.query.filter(SnapshotsLog.owner == g.user)
            .filter(SnapshotsLog.snapshot_uuid == self.snapshot_uuid)
            .order_by(SnapshotsLog.created.desc())
        )


class CustomerDetailsView(GenericMixin):
    methods = ['POST']
    form_class = CustomerDetailsForm

    def dispatch_request(self, lot_id):
        self.get_context()
        form = self.form_class(request.form, lot_id=lot_id)
        next_url = url_for('inventory.lotdevicelist', lot_id=lot_id)

        if form.validate_on_submit():
            form.save()
            messages.success('Customer details updated successfully!')
            return flask.redirect(next_url)

        messages.error('Customer details updated error!')
        for k, v in form.errors.items():
            value = ';'.join(v)
            key = form[k].label.text
            messages.error('Error {key}: {value}!'.format(key=key, value=value))
        return flask.redirect(next_url)


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
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', PER_PAGE))

        placeholder_log = PlaceholdersLog.query.filter(
            PlaceholdersLog.owner == g.user
        ).order_by(PlaceholdersLog.created.desc())

        placeholder_log = placeholder_log.paginate(page=page, per_page=per_page)
        placeholder_log.first = per_page * placeholder_log.page - per_page + 1
        placeholder_log.last = len(placeholder_log.items) + placeholder_log.first - 1

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
    '/device/<string:dhid>/document/add/',
    view_func=NewDeviceDocumentView.as_view('device_document_add'),
)
devices.add_url_rule(
    '/device/<string:dhid>/document/edit/<string:doc_id>',
    view_func=EditDeviceDocumentView.as_view('device_document_edit'),
)
devices.add_url_rule(
    '/device/<string:dhid>/document/del/<string:doc_id>',
    view_func=DeviceDocumentDeleteView.as_view('device_document_del'),
)
devices.add_url_rule(
    '/lot/<string:lot_id>/transfer-document/add/',
    view_func=NewTradeDocumentView.as_view('transfer_document_add'),
)
devices.add_url_rule(
    '/lot/<string:lot_id>/document/edit/<string:doc_id>',
    view_func=EditTransferDocumentView.as_view('transfer_document_edit'),
)
devices.add_url_rule(
    '/lot/<string:lot_id>/document/del/<string:doc_id>',
    view_func=DocumentDeleteView.as_view('document_del'),
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
    '/lot/<string:lot_id>/customerdetails/',
    view_func=CustomerDetailsView.as_view('customer_details'),
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
devices.add_url_rule(
    '/device/erasure/<int:orphans>/',
    view_func=ErasureListView.as_view('device_erasure_list_orphans'),
)
devices.add_url_rule(
    '/lot/<string:lot_id>/opentransfer/',
    view_func=OpenTransferView.as_view('open_transfer'),
)
