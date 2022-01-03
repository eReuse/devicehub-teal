from flask_wtf import FlaskForm
from wtforms import StringField, validators
from flask import g

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.lot.models import Lot


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
        id = kwargs.pop('id', None)
        self.lot = None
        if id:
            self.lot = Lot.query.filter(Lot.id == id).filter(
                Lot.owner_id == g.user.id).one()
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

        db.session.add(self.lot)
        db.session.commit()

    def remove(self):
        if self.lot and not self.lot.devices:
            self.lot.delete()
            db.session.commit()
