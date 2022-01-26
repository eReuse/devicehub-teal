import json
from flask_wtf import FlaskForm
from wtforms import StringField, validators, MultipleFileField, FloatField, IntegerField, \
                    SelectField
from flask import g, request
from sqlalchemy.util import OrderedSet
from json.decoder import JSONDecodeError

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device, Computer, Smartphone, Cellphone, \
                                                     Tablet, Monitor, Mouse, Keyboard, \
                                                     MemoryCardReader, SAI
from ereuse_devicehub.resources.action.models import RateComputer, Snapshot, VisualTest
from ereuse_devicehub.resources.action.schemas import Snapshot as SnapshotSchema
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.resources.enums import SnapshotSoftware, Severity
from ereuse_devicehub.resources.user.exceptions import InsufficientPermission
from ereuse_devicehub.resources.action.rate.v1_0 import CannotRate
from ereuse_devicehub.resources.device.sync import Sync
from ereuse_devicehub.resources.action.views.snapshot import save_json, move_json


class LotDeviceForm(FlaskForm):
    lot = StringField(u'Lot', [validators.UUID()])
    devices = StringField(u'Devices', [validators.length(min=1)])

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            return False

        self._lot = Lot.query.filter(Lot.id == self.lot.data).filter(
            Lot.owner_id == g.user.id).one()

        devices = set(self.devices.data.split(","))
        self._devices = Device.query.filter(Device.id.in_(devices)).filter(
            Device.owner_id == g.user.id).distinct().all()

        return bool(self._devices)

    def save(self):
        self._lot.devices.update(self._devices)
        db.session.add(self._lot)
        db.session.commit()

    def remove(self):
        self._lot.devices.difference_update(self._devices)
        db.session.add(self._lot)
        db.session.commit()


class LotForm(FlaskForm):
    name = StringField(u'Name', [validators.length(min=1)])

    def __init__(self, *args, **kwargs):
        self.id = kwargs.pop('id', None)
        self.instance = None
        if self.id:
            self.instance = Lot.query.filter(Lot.id == self.id).filter(
                Lot.owner_id == g.user.id).one()
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
        if self.instance and not self.instance.devices:
            self.instance.delete()
            db.session.commit()
        return self.instance


class UploadSnapshotForm(FlaskForm):
    snapshot = MultipleFileField(u'Select a Snapshot File', [validators.DataRequired()])

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

    def save(self):
        if any([x == 'Error' for x in self.result.values()]):
            return
        # result = []
        self.sync = Sync()
        schema = SnapshotSchema()
        # self.tmp_snapshots = app.config['TMP_SNAPSHOTS']
        # TODO @cayop get correct var config
        self.tmp_snapshots = '/tmp/'
        for filename, snapshot_json in self.snapshots:
            path_snapshot = save_json(snapshot_json, self.tmp_snapshots, g.user.email)
            snapshot_json.pop('debug', None)
            snapshot_json = schema.load(snapshot_json)
            response = self.build(snapshot_json)

            if hasattr(response, 'type'):
                self.result[filename] = 'Ok'
            else:
                self.result[filename] = 'Error'

            move_json(self.tmp_snapshots, path_snapshot, g.user.email)

        db.session.commit()
        return response

    def build(self, snapshot_json):
        # this is a copy adaptated from ereuse_devicehub.resources.action.views.snapshot
        device = snapshot_json.pop('device')  # type: Computer
        components = None
        if snapshot_json['software'] == (SnapshotSoftware.Workbench or SnapshotSoftware.WorkbenchAndroid):
            components = snapshot_json.pop('components', None)  # type: List[Component]
            if isinstance(device, Computer) and device.hid:
                device.add_mac_to_hid(components_snap=components)
        snapshot = Snapshot(**snapshot_json)

        # Remove new actions from devices so they don't interfere with sync
        actions_device = set(e for e in device.actions_one)
        device.actions_one.clear()
        if components:
            actions_components = tuple(set(e for e in c.actions_one) for c in components)
            for component in components:
                component.actions_one.clear()

        assert not device.actions_one
        assert all(not c.actions_one for c in components) if components else True
        db_device, remove_actions = self.sync.run(device, components)

        del device  # Do not use device anymore
        snapshot.device = db_device
        snapshot.actions |= remove_actions | actions_device  # Set actions to snapshot
        # commit will change the order of the components by what
        # the DB wants. Let's get a copy of the list so we preserve order
        ordered_components = OrderedSet(x for x in snapshot.components)

        # Add the new actions to the db-existing devices and components
        db_device.actions_one |= actions_device
        if components:
            for component, actions in zip(ordered_components, actions_components):
                component.actions_one |= actions
                snapshot.actions |= actions

        if snapshot.software == SnapshotSoftware.Workbench:
            # Check ownership of (non-component) device to from current.user
            if db_device.owner_id != g.user.id:
                raise InsufficientPermission()
            # Compute ratings
            try:
                rate_computer, price = RateComputer.compute(db_device)
            except CannotRate:
                pass
            else:
                snapshot.actions.add(rate_computer)
                if price:
                    snapshot.actions.add(price)
        elif snapshot.software == SnapshotSoftware.WorkbenchAndroid:
            pass  # TODO try except to compute RateMobile
        # Check if HID is null and add Severity:Warning to Snapshot
        if snapshot.device.hid is None:
            snapshot.severity = Severity.Warning

        db.session.add(snapshot)
        return snapshot


class NewDeviceForm(FlaskForm):
    type = StringField(u'Type', [validators.DataRequired()])
    label = StringField(u'Label')
    serial_number = StringField(u'Seria Number', [validators.DataRequired()])
    model = StringField(u'Model', [validators.DataRequired()])
    manufacturer = StringField(u'Manufacturer', [validators.DataRequired()])
    appearance = StringField(u'Appearance', [validators.Optional()])
    functionality = StringField(u'Functionality', [validators.Optional()])
    brand = StringField(u'Brand')
    generation = IntegerField(u'Generation')
    version = StringField(u'Version')
    weight = FloatField(u'Weight', [validators.DataRequired()])
    width = FloatField(u'Width', [validators.DataRequired()])
    height = FloatField(u'Height', [validators.DataRequired()])
    depth = FloatField(u'Depth', [validators.DataRequired()])
    variant = StringField(u'Variant', [validators.Optional()])
    sku = StringField(u'SKU', [validators.Optional()])
    image = StringField(u'Image', [validators.Optional(), validators.URL()])
    imei = IntegerField(u'IMEI', [validators.Optional()])
    meid = StringField(u'MEID', [validators.Optional()])
    resolution = IntegerField(u'Resolution width', [validators.Optional()])
    screen = FloatField(u'Screen size', [validators.Optional()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.devices = {"Smartphone": Smartphone,
                        "Tablet": Tablet,
                        "Cellphone": Cellphone,
                        "Monitor": Monitor,
                        "Mouse": Mouse,
                        "Keyboard": Keyboard,
                        "SAI": SAI,
                        "MemoryCardReader": MemoryCardReader}

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

    def validate(self, extra_validators=None):
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

        if self.imei.data:
            if not 13 < len(str(self.imei.data)) < 17:
                self.imei.errors = error
                is_valid = False

        if self.meid.data:
            meid = self.meid.data
            if not 13 < len(meid) < 17:
                is_valid = False
            try:
                int(meid, 16)
            except ValueError:
                self.meid.errors = error
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

    def save(self):

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
                 'image': self.image.data
            }
        }

        if self.appearance.data or self.functionality.data:
            json_snapshot['device']['actions'] = [{
                'type': 'VisualTest',
                'appearanceRange': self.appearance.data,
                'functionalityRange': self.functionality.data
            }]

        upload_form = UploadSnapshotForm()
        upload_form.sync = Sync()

        schema = SnapshotSchema()
        self.tmp_snapshots = '/tmp/'
        path_snapshot = save_json(json_snapshot, self.tmp_snapshots, g.user.email)
        snapshot_json = schema.load(json_snapshot)

        if self.type.data == 'Monitor':
            snapshot_json['device'].resolution_width = self.resolution.data
            snapshot_json['device'].size = self.screen.data

        if self.type.data in ['Smartphone', 'Tablet', 'Cellphone']:
            snapshot_json['device'].imei = self.imei.data
            snapshot_json['device'].meid = self.meid.data

        snapshot = upload_form.build(snapshot_json)

        move_json(self.tmp_snapshots, path_snapshot, g.user.email)
        if self.type.data == 'Monitor':
            snapshot.device.resolution = self.resolution.data
            snapshot.device.screen = self.screen.data

        db.session.commit()
        return snapshot


class TagForm(FlaskForm):
    code = StringField(u'Code', [validators.length(min=1)])

    def validate(self, extra_validators=None):
        error = ["This value is being used"]
        is_valid = super().validate(extra_validators)
        if not is_valid:
            return False
        tag = Tag.query.filter(Tag.id==self.code.data).all()
        if tag:
            self.code.errors = error
            return False

        return True

    def save(self):
        self.instance = Tag(id=self.code.data)
        db.session.add(self.instance)
        db.session.commit()
        return self.instance

    def remove(self):
        if not self.instance.device and not self.instance.provider:
            self.instance.delete()
            db.session.commit()
        return self.instance


class TagUnnamedForm(FlaskForm):
    amount = IntegerField(u'amount')

    def save(self):
        num = self.amount.data
        tags_id, _ = g.tag_provider.post('/', {}, query=[('num', num)])
        tags = [Tag(id=tag_id, provider=g.inventory.tag_provider) for tag_id in tags_id]
        db.session.add_all(tags)
        db.session.commit()
        return tags


class TagDeviceForm(FlaskForm):
    tag = SelectField(u'Tag', choices=[])
    device = StringField(u'Device', [validators.Optional()])

    def __init__(self, *args, **kwargs):
        self.delete = kwargs.pop('delete', None)
        self.device_id = kwargs.pop('device', None)

        # import pdb; pdb.set_trace()
        super().__init__(*args, **kwargs)

        if self.delete:
            tags = Tag.query.filter(Tag.owner_id==g.user.id).filter(Tag.device_id==self.device_id)
        else:
            tags = Tag.query.filter(Tag.owner_id==g.user.id).filter(Tag.device_id==None)

        self.tag.choices = [(tag.id, tag.id) for tag in tags]

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            return False

        self._tag = Tag.query.filter(Tag.id == self.tag.data).filter(
            Tag.owner_id == g.user.id).one()

        if self.device.data:
            try:
                self.device.data = int(self.device.data.split(',')[-1])
            except:
                self.device.data = None

        if self.device_id or self.device.data:
            self.device_id = self.device_id or self.device.data
            self._device = Device.query.filter(Device.id == self.device_id).filter(
                Device.owner_id == g.user.id).one()

        return True

    def save(self):
        self._tag.device_id = self._device.id
        db.session.add(self._tag)
        db.session.commit()

    def remove(self):
        self._tag.device = None
        db.session.add(self._tag)
        db.session.commit()


class NewActionForm(FlaskForm):
    name = StringField(u'Name')
    date = StringField(u'Date')
    severity = StringField(u'Severity')
    description = StringField(u'Description')
