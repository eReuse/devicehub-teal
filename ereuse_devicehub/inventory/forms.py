from flask_wtf import FlaskForm
from wtforms import StringField, validators
from flask_login import current_user

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
