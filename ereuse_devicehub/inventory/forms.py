import json
from flask_wtf import FlaskForm
from wtforms import StringField, validators, MultipleFileField, FloatField, IntegerField
from flask import g, request
from sqlalchemy.util import OrderedSet
from json.decoder import JSONDecodeError

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device, Computer, Smartphone, Cellphone, \
                                                     Tablet, Monitor, Mouse, Keyboard, \
                                                     MemoryCardReader, SAI
from ereuse_devicehub.resources.action.models import RateComputer, Snapshot
from ereuse_devicehub.resources.action.schemas import Snapshot as SnapshotSchema
from ereuse_devicehub.resources.lot.models import Lot
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
        self._devices = set(Device.query.filter(Device.id.in_(devices)).filter(
            Device.owner_id == g.user.id).all())

        if not self._devices:
            return False

        return True

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
    appearance = StringField(u'Appearance')
    functionality = StringField(u'Functionality')
    brand = StringField(u'Brand')
    generation = IntegerField(u'Generation')
    version = StringField(u'Version')
    weight = FloatField(u'Weight', [validators.DataRequired()])
    width = FloatField(u'Width', [validators.DataRequired()])
    height = FloatField(u'Height', [validators.DataRequired()])
    depth = FloatField(u'Depth', [validators.DataRequired()])
    variant = StringField(u'Variant')
    sku = StringField(u'SKU')
    image = StringField(u'Image', [validators.Optional(), validators.URL()])
    imei = StringField(u'IMEI')
    meid = StringField(u'MEID')
    resolution = StringField(u'Resolution width')
    screen = StringField(u'Screen size')

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
            self.generation.data = 0

        if not self.weight.data:
            self.weight.data = 0.1

        if not self.height.data:
            self.height.data = 0.1

        if not self.width.data:
            self.width.data = 0.1

        if not self.depth.data:
            self.depth.data = 0.1

        if self.type.data:
            self.instance = self.devices[self.type.data]()
            self.populate_obj(self.instance)

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            return False

        if self.generation.data < 0:
            return False

        if self.weight.data < 0.1:
            return False

        if self.height.data < 0.1:
            return False

        if self.width.data < 0.1:
            return False

        if self.depth.data < 0.1:
            return False

        return True

    def save(self):
        db.session.add(self.instance)
        import pdb; pdb.set_trace()
        db.session.commit()
        return self.instance


class NewActionForm(FlaskForm):
    name = StringField(u'Name')
    date = StringField(u'Date')
    severity = StringField(u'Severity')
    description = StringField(u'Description')
