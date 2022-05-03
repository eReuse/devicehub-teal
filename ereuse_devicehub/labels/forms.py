from flask import g
from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, validators

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.tag.model import Tag


class TagForm(FlaskForm):
    code = StringField('Code', [validators.length(min=1)])

    def validate(self, extra_validators=None):
        error = ["This value is being used"]
        is_valid = super().validate(extra_validators)
        if not is_valid:
            return False
        tag = Tag.query.filter(Tag.id == self.code.data).all()
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
    amount = IntegerField('amount')

    def save(self):
        num = self.amount.data
        tags_id, _ = g.tag_provider.post('/', {}, query=[('num', num)])
        tags = [Tag(id=tag_id, provider=g.inventory.tag_provider) for tag_id in tags_id]
        db.session.add_all(tags)
        db.session.commit()
        return tags


class PrintLabelsForm(FlaskForm):
    devices = StringField(render_kw={'class': "devicesList d-none"})

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not self.devices.data:
            return False

        device_ids = self.devices.data.split(",")
        self._devices = (
            Device.query.filter(Device.id.in_(device_ids))
            .filter(Device.owner_id == g.user.id)
            .distinct()
            .all()
        )

        if not self._devices:
            return False

        return is_valid
