import copy
import datetime
import json
from json.decoder import JSONDecodeError

import pandas as pd
from boltons.urlutils import URL
from flask import current_app as app
from flask import g, request
from flask_wtf import FlaskForm
from marshmallow import ValidationError
from sqlalchemy import or_
from sqlalchemy.util import OrderedSet
from wtforms import (
    BooleanField,
    DateField,
    FileField,
    FloatField,
    Form,
    HiddenField,
    IntegerField,
    MultipleFileField,
    SelectField,
    StringField,
    TextAreaField,
    URLField,
    validators,
)
from wtforms.fields import FormField

from ereuse_devicehub.db import db
from ereuse_devicehub.inventory.models import DeliveryNote, ReceiverNote, Transfer
from ereuse_devicehub.parser.models import PlaceholdersLog
from ereuse_devicehub.parser.parser import ParseSnapshotLsHw
from ereuse_devicehub.parser.schemas import Snapshot_lite
from ereuse_devicehub.resources.action.models import Snapshot, Trade
from ereuse_devicehub.resources.action.schemas import Snapshot as SnapshotSchema
from ereuse_devicehub.resources.action.views.snapshot import (
    SnapshotMixin,
    move_json,
    save_json,
)
from ereuse_devicehub.resources.device.models import (
    SAI,
    Cellphone,
    ComputerMonitor,
    Desktop,
    Device,
    Keyboard,
    Laptop,
    MemoryCardReader,
    Mouse,
    Placeholder,
    Server,
    Smartphone,
    Tablet,
)
from ereuse_devicehub.resources.documents.models import DataWipeDocument
from ereuse_devicehub.resources.enums import Severity
from ereuse_devicehub.resources.hash_reports import insert_hash
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.resources.tradedocument.models import TradeDocument
from ereuse_devicehub.resources.user.models import User

DEVICES = {
    "All": ["All Devices"],
    "Computer": [
        "All Computers",
        "Desktop",
        "Laptop",
        "Server",
    ],
    "Monitor": [
        "All Monitors",
        "ComputerMonitor",
        "Monitor",
        "TelevisionSet",
        "Projector",
    ],
    "Mobile, tablet & smartphone": [
        "All Mobile",
        "Mobile",
        "Tablet",
        "Smartphone",
        "Cellphone",
    ],
}

COMPUTERS = ['Desktop', 'Laptop', 'Server', 'Computer']

MONITORS = ["ComputerMonitor", "Monitor", "TelevisionSet", "Projector"]
MOBILE = ["Mobile", "Tablet", "Smartphone", "Cellphone"]


class AdvancedSearchForm(FlaskForm):
    q = StringField('Search', [validators.length(min=1)])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dhids = [x.strip() for x in self.q.data.split(' ')]
        if ',' in self.q.data:
            dhids = [x.strip() for x in self.q.data.split(',')]
        if ';' in self.q.data:
            dhids = [x.strip() for x in self.q.data.split(';')]

        self.devices = []
        if dhids:
            self.search(dhids)

    def search(self, dhids):
        self.devices = Device.query.filter(Device.devicehub_id.in_(dhids))


class FilterForm(FlaskForm):
    filter = SelectField(
        '', choices=DEVICES, default="All Computers", render_kw={'class': "form-select"}
    )

    def __init__(self, lots, lot_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lots = lots
        self.lot_id = lot_id
        self.only_unassigned = kwargs.pop('only_unassigned', True)
        self._get_types()

    def _get_types(self):
        types_of_devices = [item for sublist in DEVICES.values() for item in sublist]
        dev = request.args.get('filter')
        self.device_type = dev if dev in types_of_devices else None
        if self.device_type:
            self.filter.data = self.device_type

    def filter_from_lots(self):
        if self.lot_id:
            self.lot = self.lots.filter(Lot.id == self.lot_id).one()
            device_ids = (d.id for d in self.lot.devices)
            self.devices = Device.query.filter(Device.id.in_(device_ids)).filter(
                Device.binding == None
            )
        else:
            self.devices = Device.query.filter(Device.owner_id == g.user.id).filter(
                Device.binding == None
            )
            if self.only_unassigned:
                self.devices = self.devices.filter_by(lots=None)

    def search(self):
        self.filter_from_lots()
        filter_type = None
        if self.device_type:
            filter_type = [self.device_type]
        else:
            # Case without Filter
            filter_type = COMPUTERS

        # Generic Filters
        if "All Devices" == self.device_type:
            filter_type = COMPUTERS + MONITORS + MOBILE

        elif "All Computers" == self.device_type:
            filter_type = COMPUTERS

        elif "All Monitors" == self.device_type:
            filter_type = MONITORS

        elif "All Mobile" == self.device_type:
            filter_type = MOBILE

        if filter_type:
            self.devices = self.devices.filter(Device.type.in_(filter_type))

        return self.devices.order_by(Device.updated.desc())


class LotForm(FlaskForm):
    name = StringField('Name', [validators.length(min=1)])

    def __init__(self, *args, **kwargs):
        self.id = kwargs.pop('id', None)
        self.instance = None
        if self.id:
            self.instance = (
                Lot.query.filter(Lot.id == self.id)
                .filter(Lot.owner_id == g.user.id)
                .one()
            )
        super().__init__(*args, **kwargs)
        if self.instance and not self.name.data:
            self.name.data = self.instance.name

    def save(self):
        if not self.id:
            self.instance = Lot(name=self.name.data)

        self.populate_obj(self.instance)

        if not self.id:
            self.id = self.instance.id
            db.session.add(self.instance)
            db.session.commit()
            return self.id

        db.session.commit()
        return self.id

    def remove(self):
        if self.instance and not self.instance.trade:
            self.instance.delete()
            db.session.commit()
        return self.instance


class UploadSnapshotForm(SnapshotMixin, FlaskForm):
    snapshot = MultipleFileField('Select a Snapshot File', [validators.DataRequired()])

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            return False

        data = request.files.getlist(self.snapshot.name)
        if not data:
            return False
        self.snapshots = []
        self.result = {}
        for d in data:
            filename = d.filename
            self.result[filename] = 'Not processed'
            d = d.stream.read()
            if not d:
                self.result[filename] = 'Error this snapshot is empty'
                continue

            try:
                d_json = json.loads(d)
            except JSONDecodeError:
                self.result[filename] = 'Error this snapshot is not a json'
                continue

            uuid_snapshot = d_json.get('uuid')
            if Snapshot.query.filter(Snapshot.uuid == uuid_snapshot).all():
                self.result[filename] = 'Error this snapshot exist'
                continue

            self.snapshots.append((filename, d_json))

        if not self.snapshots:
            return False

        return True

    def is_wb_lite_snapshot(self, version: str) -> bool:
        is_lite = False
        if version in app.config['SCHEMA_WORKBENCH']:
            is_lite = True

        return is_lite

    def save(self, commit=True):
        if any([x == 'Error' for x in self.result.values()]):
            return
        schema = SnapshotSchema()
        schema_lite = Snapshot_lite()
        devices = []
        self.tmp_snapshots = app.config['TMP_SNAPSHOTS']
        for filename, snapshot_json in self.snapshots:
            path_snapshot = save_json(snapshot_json, self.tmp_snapshots, g.user.email)
            debug = snapshot_json.pop('debug', None)
            self.version = snapshot_json.get('schema_api')
            self.uuid = snapshot_json.get('uuid')
            self.sid = snapshot_json.get('sid')

            if self.is_wb_lite_snapshot(self.version):
                self.snapshot_json = schema_lite.load(snapshot_json)
                snapshot_json = ParseSnapshotLsHw(self.snapshot_json).snapshot_json
            else:
                self.version = snapshot_json.get('version')
                system_uuid = self.get_uuid(debug)
                if system_uuid:
                    snapshot_json['device']['system_uuid'] = system_uuid

            try:
                snapshot_json = schema.load(snapshot_json)
            except ValidationError as err:
                txt = "{}".format(err)
                self.errors(txt=txt)
                self.result[filename] = 'Error'
                continue

            response = self.build(snapshot_json)
            db.session.add(response)
            devices.append(response.device)

            if hasattr(response, 'type'):
                self.result[filename] = 'Ok'
                self.errors(txt="Ok", severity=Severity.Info, snapshot=response)
            else:
                self.result[filename] = 'Error'

            move_json(self.tmp_snapshots, path_snapshot, g.user.email)

        if commit:
            db.session.commit()
        return self.result, devices


class NewDeviceForm(FlaskForm):
    type = StringField('Type', [validators.DataRequired()])
    amount = IntegerField(
        'Amount',
        [validators.DataRequired(), validators.NumberRange(min=1, max=100)],
        default=1,
    )
    id_device_supplier = StringField('Id Supplier', [validators.Optional()])
    phid = StringField('Placeholder Hardware identity (Phid)', [validators.Optional()])
    pallet = StringField('Identity of pallet', [validators.Optional()])
    info = TextAreaField('Info', [validators.Optional()])
    serial_number = StringField('Seria Number', [validators.Optional()])
    model = StringField('Model', [validators.Optional()])
    manufacturer = StringField('Manufacturer', [validators.Optional()])
    appearance = StringField('Appearance', [validators.Optional()])
    functionality = StringField('Functionality', [validators.Optional()])
    brand = StringField('Brand')
    generation = IntegerField('Generation')
    version = StringField('Version')
    weight = FloatField('Weight', [validators.Optional()])
    width = FloatField('Width', [validators.Optional()])
    height = FloatField('Height', [validators.Optional()])
    depth = FloatField('Depth', [validators.Optional()])
    variant = StringField('Variant', [validators.Optional()])
    sku = StringField('SKU', [validators.Optional()])
    image = StringField('Image', [validators.Optional(), validators.URL()])
    imei = IntegerField('IMEI', [validators.Optional()])
    meid = StringField('MEID', [validators.Optional()])
    resolution = IntegerField('Resolution width', [validators.Optional()])
    screen = FloatField('Screen size', [validators.Optional()])

    def __init__(self, *args, **kwargs):
        self.objs = set()
        self._obj = kwargs.pop('_obj', None)
        super().__init__(*args, **kwargs)
        if self._obj:
            self.type.data = self._obj.type
        if not request.form:
            self.reset_from_obj()
        self.devices = {
            "Laptop": Laptop,
            "Desktop": Desktop,
            "Server": Server,
            "Smartphone": Smartphone,
            "Tablet": Tablet,
            "Cellphone": Cellphone,
            "ComputerMonitor": ComputerMonitor,
            "Mouse": Mouse,
            "Keyboard": Keyboard,
            "SAI": SAI,
            "MemoryCardReader": MemoryCardReader,
        }

        if not self.generation.data:
            self.generation.data = 1

        if not self.weight.data:
            self.weight.data = 0.1

        if not self.height.data:
            self.height.data = 0.1

        if not self.width.data:
            self.width.data = 0.1

        if not self.depth.data:
            self.depth.data = 0.1

    def reset_from_obj(self):
        if not self._obj:
            return
        disabled = {'disabled': "disabled"}
        appearance = self._obj.appearance()
        functionality = self._obj.functionality()
        if appearance:
            appearance = appearance.name
        if functionality:
            functionality = functionality.name
        self.type.render_kw = disabled
        self.type.data = self._obj.type
        self.amount.render_kw = disabled
        self.id_device_supplier.data = self._obj.placeholder.id_device_supplier
        self.phid.data = self._obj.placeholder.phid
        self.pallet.data = self._obj.placeholder.pallet
        self.info.data = self._obj.placeholder.info
        self.serial_number.data = self._obj.serial_number
        self.model.data = self._obj.model
        self.manufacturer.data = self._obj.manufacturer
        self.appearance.data = appearance
        self.functionality.data = functionality
        self.brand.data = self._obj.brand
        self.generation.data = self._obj.generation
        self.version.data = self._obj.version
        self.weight.data = self._obj.weight
        self.width.data = self._obj.width
        self.height.data = self._obj.height
        self.depth.data = self._obj.depth
        self.variant.data = self._obj.variant
        self.sku.data = self._obj.sku
        self.image.data = self._obj.image
        if self._obj.type in ['Smartphone', 'Tablet', 'Cellphone']:
            self.imei.data = self._obj.imei
            self.meid.data = self._obj.meid
        if self._obj.type == 'ComputerMonitor':
            self.resolution.data = self._obj.resolution_width
            self.screen.data = self._obj.size

        if self._obj.placeholder.is_abstract:
            self.type.render_kw = disabled
            self.amount.render_kw = disabled
            self.id_device_supplier.render_kw = disabled
            self.pallet.render_kw = disabled
            self.info.render_kw = disabled
            self.serial_number.render_kw = disabled
            self.model.render_kw = disabled
            self.manufacturer.render_kw = disabled
            self.appearance.render_kw = disabled
            self.functionality.render_kw = disabled
            self.brand.render_kw = disabled
            self.generation.render_kw = disabled
            self.version.render_kw = disabled
            self.weight.render_kw = disabled
            self.width.render_kw = disabled
            self.height.render_kw = disabled
            self.depth.render_kw = disabled
            self.variant.render_kw = disabled
            self.sku.render_kw = disabled
            self.image.render_kw = disabled
            if self._obj.type in ['Smartphone', 'Tablet', 'Cellphone']:
                self.imei.render_kw = disabled
                self.meid.render_kw = disabled
            if self._obj.type == 'ComputerMonitor':
                self.resolution.render_kw = disabled
                self.screen.render_kw = disabled

    def validate(self, extra_validators=None):  # noqa: C901
        error = ["Not a correct value"]
        is_valid = super().validate(extra_validators)

        if self.generation.data < 1:
            self.generation.errors = error
            is_valid = False

        if self.weight.data < 0.1:
            self.weight.errors = error
            is_valid = False

        if self.height.data < 0.1:
            self.height.errors = error
            is_valid = False

        if self.width.data < 0.1:
            self.width.errors = error
            is_valid = False

        if self.depth.data < 0.1:
            self.depth.errors = error
            is_valid = False

        if self.imei.data and self.amount.data == 1:
            if not 13 < len(str(self.imei.data)) < 17:
                self.imei.errors = error
                is_valid = False

        if self.meid.data and self.amount.data == 1:
            meid = self.meid.data
            if not 13 < len(meid) < 17:
                is_valid = False
            try:
                int(meid, 16)
            except ValueError:
                self.meid.errors = error
                is_valid = False

        if self.phid.data and self.amount.data == 1 and not self._obj:
            dev = Placeholder.query.filter(
                Placeholder.phid == self.phid.data, Placeholder.owner == g.user
            ).first()
            if dev:
                msg = "Sorry, exist one snapshot device with this HID"
                self.phid.errors = [msg]
                is_valid = False

        if (
            self.phid.data
            and self._obj
            and self.phid.data != self._obj.placeholder.phid
        ):
            dev = Placeholder.query.filter(
                Placeholder.phid == self.phid.data, Device.owner == g.user
            ).first()
            if dev:
                msg = "Sorry, exist one snapshot device with this HID"
                self.phid.errors = [msg]
                is_valid = False

        if not is_valid:
            return False

        if self.image.data == '':
            self.image.data = None
        if self.manufacturer.data:
            self.manufacturer.data = self.manufacturer.data.lower()
        if self.model.data:
            self.model.data = self.model.data.lower()
        if self.serial_number.data:
            self.serial_number.data = self.serial_number.data.lower()

        return True

    def save(self, commit=True):
        if self._obj:
            self.edit_device()
        else:
            for n in range(self.amount.data):
                self.reset_ids()
                self.create_device()

        if commit:
            db.session.commit()

    def create_device(self):
        schema = SnapshotSchema()
        json_snapshot = {
            'type': 'Snapshot',
            'software': 'Web',
            'version': '11.0',
            'device': {
                'type': self.type.data,
                'model': self.model.data,
                'manufacturer': self.manufacturer.data,
                'serialNumber': self.serial_number.data,
                'brand': self.brand.data,
                'version': self.version.data,
                'generation': self.generation.data,
                'sku': self.sku.data,
                'weight': self.weight.data,
                'width': self.width.data,
                'height': self.height.data,
                'depth': self.depth.data,
                'variant': self.variant.data,
                'image': self.image.data,
            },
        }

        if self.appearance.data or self.functionality.data:
            json_snapshot['device']['actions'] = [
                {
                    'type': 'VisualTest',
                    'appearanceRange': self.appearance.data,
                    'functionalityRange': self.functionality.data,
                }
            ]
        snapshot_json = schema.load(json_snapshot)
        device = snapshot_json['device']

        if self.type.data == 'ComputerMonitor':
            device.resolution_width = self.resolution.data
            device.size = self.screen.data

        if self.type.data in ['Smartphone', 'Tablet', 'Cellphone']:
            device.imei = self.imei.data
            device.meid = self.meid.data

        device.placeholder = self.get_placeholder()
        db.session.add(device)

        placeholder_log = PlaceholdersLog(
            type="New device", source='Web form', placeholder=device.placeholder
        )
        db.session.add(placeholder_log)
        self.objs.add(device)

    def reset_ids(self):
        if self.amount.data > 1:
            self.phid.data = None
            self.id_device_supplier.data = None
            self.serial_number.data = None
            self.sku.data = None
            self.imei.data = None
            self.meid.data = None

    def get_placeholder(self):
        self.placeholder = Placeholder(
            **{
                'phid': self.phid.data or None,
                'id_device_supplier': self.id_device_supplier.data,
                'info': self.info.data,
                'pallet': self.pallet.data,
                'is_abstract': False,
            }
        )
        return self.placeholder

    def edit_device(self):
        self._obj.placeholder.phid = self.phid.data or self._obj.placeholder.phid
        if not self._obj.placeholder.is_abstract:
            self._obj.placeholder.id_device_supplier = (
                self.id_device_supplier.data or None
            )
            self._obj.placeholder.info = self.info.data or None
            self._obj.placeholder.pallet = self.pallet.data or None
            self._obj.model = self.model.data
            self._obj.manufacturer = self.manufacturer.data
            self._obj.serial_number = self.serial_number.data
            self._obj.brand = self.brand.data
            self._obj.version = self.version.data
            self._obj.generation = self.generation.data
            self._obj.sku = self.sku.data
            self._obj.weight = self.weight.data
            self._obj.width = self.width.data
            self._obj.height = self.height.data
            self._obj.depth = self.depth.data
            self._obj.variant = self.variant.data
            self._obj.image = self.image.data

            if self._obj.type == 'ComputerMonitor':
                self._obj.resolution_width = self.resolution.data
                self._obj.size = self.screen.data

            if self._obj.type in ['Smartphone', 'Tablet', 'Cellphone']:
                self._obj.imei = self.imei.data
                self._obj.meid = self.meid.data

            if (
                self.appearance.data
                and self.appearance.data != self._obj.appearance().name
            ):
                self._obj.set_appearance(self.appearance.data)

            if (
                self.functionality.data
                and self.functionality.data != self._obj.functionality().name
            ):
                self._obj.set_functionality(self.functionality.data)

        placeholder_log = PlaceholdersLog(
            type="Update", source='Web form', placeholder=self._obj.placeholder
        )
        db.session.add(placeholder_log)


class TagDeviceForm(FlaskForm):
    tag = SelectField('Tag', choices=[])
    device = StringField('Device', [validators.Optional()])

    def __init__(self, *args, **kwargs):
        self.delete = kwargs.pop('delete', None)
        self.device_id = kwargs.pop('device', None)

        super().__init__(*args, **kwargs)

        if self.delete:
            tags = (
                Tag.query.filter(Tag.owner_id == g.user.id)
                .filter_by(device_id=self.device_id)
                .order_by(Tag.id)
            )
        else:
            tags = (
                Tag.query.filter(Tag.owner_id == g.user.id)
                .filter_by(device_id=None)
                .order_by(Tag.id)
            )

        self.tag.choices = [(tag.id, tag.id) for tag in tags]

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            return False

        self._tag = (
            Tag.query.filter(Tag.id == self.tag.data)
            .filter(Tag.owner_id == g.user.id)
            .one()
        )

        if not self.delete and self._tag.device_id:
            self.tag.errors = [("This tag is actualy in use.")]
            return False

        if self.device.data:
            try:
                self.device.data = int(self.device.data.split(',')[-1])
            except:  # noqa: E722
                self.device.data = None

        if self.device_id or self.device.data:
            self.device_id = self.device_id or self.device.data
            self._device = (
                Device.query.filter(Device.id == self.device_id)
                .filter(Device.owner_id == g.user.id)
                .one()
            )

        return True

    def save(self):
        self._tag.device_id = self._device.id
        db.session.add(self._tag)
        db.session.commit()

    def remove(self):
        self._tag.device = None
        db.session.add(self._tag)
        db.session.commit()


class ActionFormMixin(FlaskForm):
    name = StringField(
        'Name',
        [validators.length(max=50)],
        description="A name or title of the event. Something to look for.",
    )
    devices = HiddenField()
    date = DateField(
        'Date',
        [validators.Optional()],
        description="""When the action ends. For some actions like booking
                                    the time when it expires, for others like renting the
                                    time that the end rents. For specific actions, it is the
                                    time in which they are carried out; differs from created
                                    in that created is where the system receives the action.""",
    )
    severity = SelectField(
        'Severity',
        choices=[(v.name, v.name) for v in Severity],
        description="""An indicator that evaluates the execution of the event.
                                          For example, failed events are set to Error""",
    )
    description = TextAreaField('Description')
    lot = HiddenField()
    type = HiddenField()

    def validate(self, extra_validators=None):
        is_valid = self.generic_validation(extra_validators=extra_validators)

        if not is_valid:
            return False

        if self.type.data in [None, '']:
            return False

        if not self.devices.data:
            return False

        self._devices = OrderedSet()

        devices = set(self.devices.data.split(","))
        self._devices = OrderedSet(
            Device.query.filter(Device.id.in_(devices))
            .filter(Device.owner_id == g.user.id)
            .all()
        )

        if not self._devices:
            return False

        return True

    def generic_validation(self, extra_validators=None):
        # Some times we want check validations without devices list
        return super().validate(extra_validators)

    def save(self):
        Model = db.Model._decl_class_registry.data[self.type.data]()
        self.instance = Model()
        devices = self.devices.data
        severity = self.severity.data
        self.devices.data = self._devices
        self.severity.data = Severity[self.severity.data]

        self.populate_obj(self.instance)
        db.session.add(self.instance)
        db.session.commit()

        self.devices.data = devices
        self.severity.data = severity

        return self.instance

    def check_valid(self):
        if self.type.data in ['', None]:
            return

        if not self.validate():
            return self.type.data


class NewActionForm(ActionFormMixin):
    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            return False

        if self.type.data in ['Allocate', 'Deallocate', 'Trade', 'DataWipe']:
            return False

        return True


class AllocateForm(ActionFormMixin):
    date = HiddenField('')
    start_time = DateField('Start time')
    end_time = DateField('End time', [validators.Optional()])
    final_user_code = StringField(
        'Final user code', [validators.Optional(), validators.length(max=50)]
    )
    transaction = StringField(
        'Transaction', [validators.Optional(), validators.length(max=50)]
    )
    end_users = IntegerField('Number of end users', [validators.Optional()])

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False

        if self.type.data not in ['Allocate', 'Deallocate']:
            return False

        if not self.validate_dates():
            return False

        if not self.check_devices():
            return False

        return True

    def validate_dates(self):
        start_time = self.start_time.data
        end_time = self.end_time.data

        if not start_time:
            self.start_time.errors = ['Not a valid date value.!']
            return False

        if start_time > datetime.datetime.now().date():
            self.start_time.errors = ['Not a valid date value.!']
            return False

        if start_time and end_time and end_time < start_time:
            error = ['The action cannot finish before it starts.']
            self.end_time.errors = error
            return False

        if not end_time:
            self.end_time.data = self.start_time.data

        return True

    def check_devices(self):
        if self.type.data == 'Allocate':
            return self.check_allocate()
        if self.type.data == 'Deallocate':
            return self.check_deallocate()
        return True

    def check_allocate(self):
        txt = "You need deallocate before allocate this device again"
        for device in self._devices:
            # |  Allo  -  Deallo  |  Allo  -  Deallo  |

            allocates = [
                ac for ac in device.actions if ac.type in ['Allocate', 'Deallocate']
            ]
            allocates.sort(key=lambda x: x.start_time)
            allocates.reverse()
            last_deallocate = None
            last_allocate = None
            for ac in allocates:
                if (
                    ac.type == 'Deallocate'
                    and ac.start_time.date() < self.start_time.data
                ):
                    # allow to do the action
                    break

                # check if this action is between an old allocate - deallocate
                if ac.type == 'Deallocate':
                    last_deallocate = ac
                    continue

                if (
                    ac.type == 'Allocate'
                    and ac.start_time.date() > self.start_time.data
                ):
                    last_deallocate = None
                    last_allocate = None
                    continue

                if ac.type == 'Allocate':
                    last_allocate = ac

                if last_allocate or not last_deallocate:
                    self.devices.errors = [txt]
                    return False

            device.allocated = True
        return True

    def check_deallocate(self):
        txt = "Sorry some of this devices are actually deallocate"
        for device in self._devices:
            allocates = [
                ac for ac in device.actions if ac.type in ['Allocate', 'Deallocate']
            ]
            allocates.sort(key=lambda x: x.start_time)
            allocates.reverse()
            last_deallocate = None
            last_allocate = None

            for ac in allocates:
                # check if this action is between an old allocate - deallocate
                # |  Allo  -  Deallo  |  Allo  -  Deallo  |
                # |  Allo  |
                if (
                    ac.type == 'Allocate'
                    and ac.start_time.date() > self.start_time.data
                ):
                    last_allocate = None
                    last_deallocate = None
                    continue

                if ac.type == 'Allocate' and not last_deallocate:
                    last_allocate = ac
                    break

                if (
                    ac.type == 'Deallocate'
                    and ac.start_time.date() > self.start_time.data
                ):
                    last_deallocate = ac
                    continue

                if ac.type == 'Deallocate':
                    last_allocate = None

                if last_deallocate or not last_allocate:
                    self.devices.errors = [txt]
                    return False

            if not last_deallocate and not last_allocate:
                self.devices.errors = [txt]
                return False

            device.allocated = False
        return True


class DataWipeDocumentForm(Form):
    date = DateField(
        'Date', [validators.Optional()], description="Date when was data wipe"
    )
    url = URLField(
        'Url', [validators.Optional()], description="Url where the document resides"
    )
    success = BooleanField(
        'Success', [validators.Optional()], description="The erase was success or not?"
    )
    software = StringField(
        'Software',
        [validators.Optional()],
        description="Which software has you use for erase the disks",
    )
    id_document = StringField(
        'Document Id',
        [validators.Optional()],
        description="Identification number of document",
    )
    file_name = FileField(
        'File',
        [validators.DataRequired()],
        description="""This file is not stored on our servers, it is only used to
                                  generate a digital signature and obtain the name of the file.""",
    )

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        return is_valid

    def save(self, commit=True):
        file_name = ''
        file_hash = ''
        if self.file_name.data:
            file_name = self.file_name.data.filename
            file_hash = insert_hash(self.file_name.data.read(), commit=False)

        self.url.data = URL(self.url.data)
        self._obj = DataWipeDocument(
            document_type='DataWipeDocument',
        )
        self.populate_obj(self._obj)
        self._obj.file_name = file_name
        self._obj.file_hash = file_hash
        db.session.add(self._obj)
        if commit:
            db.session.commit()

        return self._obj


class DataWipeForm(ActionFormMixin):
    document = FormField(DataWipeDocumentForm)

    def save(self):
        self.document.form.save(commit=False)

        Model = db.Model._decl_class_registry.data[self.type.data]()
        self.instance = Model()
        devices = self.devices.data
        severity = self.severity.data
        self.devices.data = self._devices
        self.severity.data = Severity[self.severity.data]

        document = copy.copy(self.document)
        del self.document
        self.populate_obj(self.instance)
        self.instance.document = document.form._obj
        db.session.add(self.instance)
        db.session.commit()

        self.devices.data = devices
        self.severity.data = severity
        self.document = document

        return self.instance


class TradeForm(ActionFormMixin):
    user_from = StringField(
        'Supplier',
        [validators.Optional()],
        description="Please enter the supplier's email address",
        render_kw={'data-email': ""},
    )
    user_to = StringField(
        'Receiver',
        [validators.Optional()],
        description="Please enter the receiver's email address",
        render_kw={'data-email': ""},
    )
    confirm = BooleanField(
        'Confirm',
        [validators.Optional()],
        default=True,
        description="I need confirmation from the other user for every device and document.",
    )
    code = StringField(
        'Code',
        [validators.Optional()],
        description="If you don't need confirm, you need put a code for trace the user in the statistics.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_from.render_kw['data-email'] = g.user.email
        self.user_to.render_kw['data-email'] = g.user.email
        self._lot = (
            Lot.query.outerjoin(Trade)
            .filter(Lot.id == self.lot.data)
            .filter(
                or_(
                    Trade.user_from == g.user,
                    Trade.user_to == g.user,
                    Lot.owner_id == g.user.id,
                )
            )
            .one()
        )

    def validate(self, extra_validators=None):
        is_valid = self.generic_validation(extra_validators=extra_validators)
        email_from = self.user_from.data
        email_to = self.user_to.data

        if self.type.data != "Trade":
            return False

        if not self.confirm.data and not self.code.data:
            self.code.errors = ["If you don't want to confirm, you need a code"]
            is_valid = False

        if (
            self.confirm.data
            and not (email_from and email_to)
            or email_to == email_from
            or g.user.email not in [email_from, email_to]
        ):

            errors = ["If you want confirm, you need a correct email"]
            self.user_to.errors = errors
            self.user_from.errors = errors

            is_valid = False

        if self.confirm.data and is_valid:
            user_to = User.query.filter_by(email=email_to).first() or g.user
            user_from = User.query.filter_by(email=email_from).first() or g.user
            if user_to == user_from:
                is_valid = False
            else:
                self.db_user_to = user_to
                self.db_user_from = user_from

        self.has_errors = not is_valid
        return is_valid

    def save(self, commit=True):
        if self.has_errors:
            raise ValueError(
                "The %s could not be saved because the data didn't validate."
                % (self.instance._meta.object_name)
            )
        if not self.confirm.data:
            self.create_phantom_account()
        self.prepare_instance()
        self.create_automatic_trade()

        if commit:
            db.session.commit()

        return self.instance

    def prepare_instance(self):
        Model = db.Model._decl_class_registry.data['Trade']()
        self.instance = Model()
        self.instance.user_from = self.db_user_from
        self.instance.user_to = self.db_user_to
        self.instance.lot_id = self._lot.id
        self.instance.devices = self._lot.devices
        self.instance.code = self.code.data
        self.instance.confirm = self.confirm.data
        self.instance.date = self.date.data
        self.instance.name = self.name.data
        self.instance.description = self.description.data
        db.session.add(self.instance)

    def create_phantom_account(self):
        """
        If exist both users not to do nothing
        If exist from but not to:
            search if exist in the DB
                if exist use it
                else create new one
        The same if exist to but not from

        """
        user_from = self.user_from.data
        user_to = self.user_to.data
        code = self.code.data

        if user_from and user_to:
            #  both users exist, no further action is necessary
            return

        # Create receiver (to) phantom account
        if user_from and not user_to:
            assert g.user.email == user_from

            self.user_from = g.user
            self.user_to = self.get_or_create_user(code)

        # Create supplier (from) phantom account
        if not user_from and user_to:
            assert g.user.email == user_to

            self.user_from = self.get_or_create_user(code)
            self.user_to = g.user

        self.db_user_to = self.user_to
        self.db_user_from = self.user_from

    def get_or_create_user(self, code):
        email = "{}_{}@dhub.com".format(str(g.user.id), code)
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, password='', active=False, phantom=True)
            db.session.add(user)
        return user

    def create_automatic_trade(self):
        # This method change the ownership of devices
        # do nothing if an explicit confirmation is required
        if self.confirm.data:
            return

        # Change the owner for every devices
        for dev in self._lot.devices:
            dev.change_owner(self.db_user_to)

    def check_valid(self):
        if self.user_from.data == self.user_to.data:
            return

        if self.user_from.data == g.user.email:
            return 'user_to'

        if self.user_to.data == g.user.email:
            return 'user_from'


class TradeDocumentForm(FlaskForm):
    url = URLField(
        'Url',
        [validators.Optional()],
        render_kw={'class': "form-control"},
        description="Url where the document resides",
    )
    description = StringField(
        'Description',
        [validators.Optional()],
        render_kw={'class': "form-control"},
        description="",
    )
    id_document = StringField(
        'Document Id',
        [validators.Optional()],
        render_kw={'class': "form-control"},
        description="Identification number of document",
    )
    date = DateField(
        'Date',
        [validators.Optional()],
        render_kw={'class': "form-control"},
        description="",
    )
    file_name = FileField(
        'File',
        [validators.DataRequired()],
        render_kw={'class': "form-control"},
        description="""This file is not stored on our servers, it is only used to
                                  generate a digital signature and obtain the name of the file.""",
    )

    def __init__(self, *args, **kwargs):
        lot_id = kwargs.pop('lot')
        super().__init__(*args, **kwargs)
        self._lot = Lot.query.filter(Lot.id == lot_id).one()

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if g.user not in [self._lot.trade.user_from, self._lot.trade.user_to]:
            is_valid = False

        return is_valid

    def save(self, commit=True):
        file_name = ''
        file_hash = ''
        if self.file_name.data:
            file_name = self.file_name.data.filename
            file_hash = insert_hash(self.file_name.data.read(), commit=False)

        self.url.data = URL(self.url.data)
        self._obj = TradeDocument(lot_id=self._lot.id)
        self.populate_obj(self._obj)
        self._obj.file_name = file_name
        self._obj.file_hash = file_hash
        db.session.add(self._obj)
        self._lot.trade.documents.add(self._obj)
        if commit:
            db.session.commit()

        return self._obj


class TransferForm(FlaskForm):
    code = StringField(
        'Code',
        [validators.DataRequired()],
        render_kw={'class': "form-control"},
        description="You need put a code for transfer the external user",
    )
    description = TextAreaField(
        'Description',
        [validators.Optional()],
        render_kw={'class': "form-control"},
    )
    type = HiddenField()

    def __init__(self, *args, **kwargs):
        self._type = kwargs.get('type')
        lot_id = kwargs.pop('lot_id', None)
        self._tmp_lot = Lot.query.filter(Lot.id == lot_id).one()
        super().__init__(*args, **kwargs)
        self._obj = None

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)
        if not self._tmp_lot:
            return False

        if self._type and self.type.data not in ['incoming', 'outgoing']:
            return False

        if self._obj and self.date.data:
            if self.date.data > datetime.datetime.now().date():
                return False

        return is_valid

    def save(self, commit=True):
        self.set_obj()
        db.session.add(self._obj)

        if commit:
            db.session.commit()

        return self._obj

    def set_obj(self):
        self.newlot = Lot(name=self._tmp_lot.name)
        self.newlot.devices = self._tmp_lot.devices
        db.session.add(self.newlot)

        self._obj = Transfer(lot=self.newlot)

        self.populate_obj(self._obj)

        if self.type.data == 'incoming':
            self._obj.user_to = g.user
        elif self.type.data == 'outgoing':
            self._obj.user_from = g.user


class EditTransferForm(TransferForm):
    date = DateField(
        'Date',
        [validators.Optional()],
        render_kw={'class': "form-control"},
        description="""Date when the transfer is closed""",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.type

        self._obj = self._tmp_lot.transfer

        if not self.data['csrf_token']:
            self.code.data = self._obj.code
            self.description.data = self._obj.description
            self.date.data = self._obj.date

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)
        date = self.date.data
        if date and date > datetime.datetime.now().date():
            self.date.errors = ["You have to choose a date before today."]
            is_valid = False
        return is_valid

    def set_obj(self, commit=True):
        self.populate_obj(self._obj)


class NotesForm(FlaskForm):
    number = StringField(
        'Number',
        [validators.Optional()],
        render_kw={'class': "form-control"},
        description="You can put a number for tracer of receiver or delivery",
    )
    date = DateField(
        'Date',
        [validators.Optional()],
        render_kw={'class': "form-control"},
        description="""Date when the transfer was do it""",
    )
    units = IntegerField(
        'Units',
        [validators.Optional()],
        render_kw={'class': "form-control"},
        description="Number of units",
    )
    weight = IntegerField(
        'Weight',
        [validators.Optional()],
        render_kw={'class': "form-control"},
        description="Weight expressed in Kg",
    )

    def __init__(self, *args, **kwargs):
        self.type = kwargs.pop('type', None)
        lot_id = kwargs.pop('lot_id', None)
        self._tmp_lot = Lot.query.filter(Lot.id == lot_id).one()
        self._obj = None
        super().__init__(*args, **kwargs)

        if self._tmp_lot.transfer:
            if self.type == 'Delivery':
                self._obj = self._tmp_lot.transfer.delivery_note
                if not self._obj:
                    self._obj = DeliveryNote(transfer_id=self._tmp_lot.transfer.id)

                self.date.description = """Date when the delivery was do it."""
                self.number.description = (
                    """You can put a number for tracer of delivery note."""
                )

            if self.type == 'Receiver':
                self._obj = self._tmp_lot.transfer.receiver_note
                if not self._obj:
                    self._obj = ReceiverNote(transfer_id=self._tmp_lot.transfer.id)

                self.date.description = """Date when the receipt was do it."""
                self.number.description = (
                    """You can put a number for tracer of receiber note."""
                )

            if self.is_editable():
                self.number.render_kw.pop('disabled', None)
                self.date.render_kw.pop('disabled', None)
                self.units.render_kw.pop('disabled', None)
                self.weight.render_kw.pop('disabled', None)
            else:
                disabled = {'disabled': "disabled"}
                self.number.render_kw.update(disabled)
                self.date.render_kw.update(disabled)
                self.units.render_kw.update(disabled)
                self.weight.render_kw.update(disabled)

        if self._obj and not self.data['csrf_token']:
            self.number.data = self._obj.number
            self.date.data = self._obj.date
            self.units.data = self._obj.units
            self.weight.data = self._obj.weight

    def is_editable(self):
        if not self._tmp_lot.transfer:
            return False

        if self._tmp_lot.transfer.closed:
            return False

        if self._tmp_lot.transfer.code:
            return True

        if self._tmp_lot.transfer.user_from == g.user and self.type == 'Receiver':
            return False

        if self._tmp_lot.transfer.user_to == g.user and self.type == 'Delivery':
            return False

        return True

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)
        date = self.date.data
        if date and date > datetime.datetime.now().date():
            self.date.errors = ["You have to choose a date before today."]
            is_valid = False

        if not self.is_editable():
            is_valid = False

        return is_valid

    def save(self, commit=True):
        if self._tmp_lot.transfer.closed:
            return self._obj

        self.populate_obj(self._obj)
        db.session.add(self._obj)

        if commit:
            db.session.commit()

        return self._obj


class UploadPlaceholderForm(FlaskForm):
    type = StringField('Type', [validators.DataRequired()])
    placeholder_file = FileField(
        'Select a Placeholder File', [validators.DataRequired()]
    )

    def get_data_file(self):
        files = request.files.getlist(self.placeholder_file.name)

        if not files:
            return False

        _file = files[0]
        if _file.content_type == 'text/csv':
            self.source = "CSV File: {}".format(_file.filename)
            delimiter = ';'
            data = pd.read_csv(_file).to_dict()
            head = list(data.keys())[0].split(delimiter)
            values = [
                {k: v.split(delimiter)} for x in data.values() for k, v in x.items()
            ]
            data = {}
            for i in range(len(head)):
                data[head[i]] = {}
                for x in values:
                    for k, v in x.items():
                        data[head[i]][k] = v[i]
        else:
            self.source = "Excel File: {}".format(_file.filename)
            try:
                data = pd.read_excel(_file).to_dict()
            except ValueError:
                self.placeholder_file.errors = ["File don't have a correct format"]
                return False

        return data

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            return False

        if not request.files.getlist(self.placeholder_file.name):
            return False

        data = self.get_data_file()
        if not data:
            return False

        header = [
            'Phid',
            'Model',
            'Manufacturer',
            'Serial Number',
            'Id device Supplier',
            'Pallet',
            'Info',
        ]

        for k in header:
            if k not in data.keys():
                self.placeholder_file.errors = ["Missing required fields in the file"]
                return False

        self.placeholders = []
        schema = SnapshotSchema()
        self.path_snapshots = {}
        for i in data['Phid'].keys():
            placeholder = None
            data['Phid'][i] = str(data['Phid'][i])
            if data['Phid'][i]:
                placeholder = Placeholder.query.filter_by(phid=data['Phid'][i]).first()

            # update one
            if placeholder:
                device = placeholder.device
                device.model = "{}".format(data['Model'][i]).lower()
                device.manufacturer = "{}".format(data['Manufacturer'][i]).lower()
                device.serial_number = "{}".format(data['Serial Number'][i]).lower()
                placeholder.id_device_supplier = "{}".format(
                    data['Id device Supplier'][i]
                )
                placeholder.pallet = "{}".format(data['Pallet'][i])
                placeholder.info = "{}".format(data['Info'][i])

                placeholder_log = PlaceholdersLog(
                    type="Update", source=self.source, placeholder=device.placeholder
                )
                self.placeholders.append((device, placeholder_log))
                continue

            # create a new one
            json_snapshot = {
                'type': 'Snapshot',
                'software': 'Web',
                'version': '11.0',
                'device': {
                    'type': self.type.data,
                    'model': "{}".format(data['Model'][i]),
                    'manufacturer': "{}".format(data['Manufacturer'][i]),
                    'serialNumber': "{}".format(data['Serial Number'][i]),
                },
            }
            json_placeholder = {
                'phid': data['Phid'][i] or None,
                'id_device_supplier': data['Id device Supplier'][i],
                'pallet': data['Pallet'][i],
                'info': data['Info'][i],
                'is_abstract': False,
            }

            snapshot_json = schema.load(json_snapshot)
            device = snapshot_json['device']
            device.placeholder = Placeholder(**json_placeholder)

            placeholder_log = PlaceholdersLog(
                type="New device", source=self.source, placeholder=device.placeholder
            )
            self.placeholders.append((device, placeholder_log))

        return True

    def save(self, commit=True):

        for device, placeholder_log in self.placeholders:
            db.session.add(device)
            db.session.add(placeholder_log)

        if commit:
            db.session.commit()

        return self.placeholders


class EditPlaceholderForm(FlaskForm):
    manufacturer = StringField('Manufacturer', [validators.Optional()])
    model = StringField('Model', [validators.Optional()])
    serial_number = StringField('Serial Number', [validators.Optional()])
    id_device_supplier = StringField('Id Supplier', [validators.Optional()])
    phid = StringField('Phid', [validators.DataRequired()])
    pallet = StringField('Pallet', [validators.Optional()])
    info = StringField('Info', [validators.Optional()])

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            return False

        return True

    def save(self, commit=True):

        for device in self.placeholders:
            db.session.add(device)

        if commit:
            db.session.commit()

        return self.placeholders


class BindingForm(FlaskForm):
    phid = StringField('Phid', [validators.DataRequired()])

    def __init__(self, *args, **kwargs):
        self.device = kwargs.pop('device', None)
        self.placeholder = kwargs.pop('placeholder', None)
        super().__init__(*args, **kwargs)

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            txt = "This placeholder not exist."
            self.phid.errors = [txt]
            return False

        if self.device.placeholder:
            txt = "This is not a device Workbench."
            self.phid.errors = [txt]
            return False

        if not self.placeholder:
            self.placeholder = Placeholder.query.filter(
                Placeholder.phid == self.phid.data, Placeholder.owner == g.user
            ).first()

        if not self.placeholder:
            txt = "This placeholder not exist."
            self.phid.errors = [txt]
            return False

        if self.placeholder.binding:
            txt = "This placeholder have a binding with other device. "
            txt += "Before you need to do an unbinding with this other device."
            self.phid.errors = [txt]
            return False

        return True
