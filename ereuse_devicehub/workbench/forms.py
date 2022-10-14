from flask import g
from flask_wtf import FlaskForm
from wtforms import StringField, validators

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Placeholder


class KangarooForm(FlaskForm):
    phid = StringField('Phid', [validators.length(min=1)])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.placeholder = None
        self.kangaroos = Placeholder.query.filter(
            Placeholder.kangaroo.is_(True)
        ).filter(Placeholder.owner_id == g.user.id)

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)
        if not is_valid:
            return False

        if not self.placeholder:
            self.placeholder = (
                Placeholder.query.filter(Placeholder.phid == self.phid.data)
                .filter(Placeholder.owner_id == g.user.id)
                .first()
            )
            if self.placeholder:
                if self.placeholder.status not in ['Snapshot', 'Twin']:
                    self.placeholder = None

        if not self.placeholder:
            self.phid.errors = ["Device not exist"]
            return False

        return True

    def save(self):
        if not self.placeholder or self.placeholder.kangaroo:
            return

        self.placeholder.kangaroo = True
        db.session.commit()
        return self.placeholder
