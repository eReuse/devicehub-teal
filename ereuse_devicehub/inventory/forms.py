from flask_wtf import FlaskForm
from wtforms import StringField, validators
from flask_login import current_user
from flask import g

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.lot.models import Lot


class LotDeviceAddForm(FlaskForm):
    lot = StringField(u'Lot', [validators.UUID()])
    devices = StringField(u'Devices', [validators.length(min=1)])

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            return False

        self.lot = Lot.query.filter(Lot.id == self.lot.data).filter(
            Lot.owner_id == current_user.id).one()

        devices = set(self.devices.data.split(","))
        self.devices = set(Device.query.filter(Device.id.in_(devices)).filter(
            Device.owner_id == current_user.id).all())

        if not self.devices:
            return False

        return True

    def save(self):
        self.lot.devices.update(self.devices)
        g.user = current_user
        db.session.add(self.lot)
        db.session.commit()


class LotForm(FlaskForm):
    name = StringField(u'Name', [validators.length(min=1)])

    def __init__(self, *args, **kwargs):
        id = kwargs.pop('id', None)
        self.lot = None
        if id:
            self.lot = Lot.query.filter(Lot.id == id).filter(
                Lot.owner_id == current_user.id).one()
        super().__init__(*args, **kwargs)
        if self.lot and not self.name.data:
            self.name.data = self.lot.name

    def save(self):
        name = self.name.data.strip()
        if self.lot:
            if self.lot.name == name:
                return
            self.lot.name = name
        else:
            self.lot = Lot(name=name)

        g.user = current_user
        db.session.add(self.lot)
        db.session.commit()
