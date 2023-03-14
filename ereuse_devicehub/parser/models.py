from citext import CIText
from flask import g
from sqlalchemy import BigInteger, Column, Sequence, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import Snapshot
from ereuse_devicehub.resources.device.models import Placeholder
from ereuse_devicehub.resources.enums import Severity
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import User


class SnapshotsLog(Thing):
    """A Snapshot log."""

    id = Column(BigInteger, Sequence('snapshots_log_seq'), primary_key=True)
    severity = Column(SmallInteger, default=Severity.Info, nullable=False)
    version = Column(CIText(), default='', nullable=True)
    description = Column(CIText(), default='', nullable=True)
    sid = Column(CIText(), nullable=True)
    snapshot_uuid = Column(UUID(as_uuid=True), nullable=True)
    snapshot_id = Column(UUID(as_uuid=True), db.ForeignKey(Snapshot.id), nullable=True)
    owner_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    snapshot = db.relationship(Snapshot, primaryjoin=snapshot_id == Snapshot.id)
    owner = db.relationship(User, primaryjoin=owner_id == User.id)

    def save(self, commit=False):
        db.session.add(self)

        if commit:
            db.session.commit()

    def get_status(self):
        if self.snapshot:
            return Severity(self.severity)

        return ''

    def get_device(self):
        if self.snapshot:
            if self.snapshot.device.binding:
                return self.snapshot.device.binding.device.devicehub_id
            return self.snapshot.device.devicehub_id

        return ''

    def get_original_dhid(self):
        if self.snapshot:
            dev = self.snapshot.device
            if dev.dhid_bk:
                return dev.dhid_bk

        return self.get_device()

    def get_type_device(self):
        if self.snapshot:
            if self.snapshot.device.binding:
                return self.snapshot.device.binding.status

        return ''

    def get_new_device(self):
        if not self.snapshot:
            return ''

        if not self.snapshot.device:
            return ''

        snapshots = []
        for s in self.snapshot.device.actions:
            if s == self.snapshot:
                break
            if s.type == self.snapshot.type:
                snapshots.append(s)
        return snapshots and 'Update' or 'New Device'

    def get_system_uuid(self):
        try:
            return self.snapshot.device.system_uuid or ''
        except AttributeError:
            return ''

    def get_version(self):
        if not self.snapshot:
            return self.version
        settings_version = self.snapshot.settings_version or ''
        settings_version = "".join([x[0] for x in settings_version.split(' ') if x])

        if settings_version:
            return "{} ({})".format(self.version, settings_version)
        return "{}".format(self.version)


class PlaceholdersLog(Thing):
    """A Placeholder log."""

    id = Column(BigInteger, Sequence('placeholders_log_seq'), primary_key=True)
    source = Column(CIText(), default='', nullable=True)
    type = Column(CIText(), default='', nullable=True)
    severity = Column(SmallInteger, default=Severity.Info, nullable=False)

    placeholder_id = Column(BigInteger, db.ForeignKey(Placeholder.id), nullable=True)
    placeholder = db.relationship(
        Placeholder,
        backref=backref(
            'placeholder_logs', lazy=True, cascade="all, delete-orphan", uselist=True
        ),
        primaryjoin=placeholder_id == Placeholder.id,
    )
    owner_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    owner = db.relationship(User, primaryjoin=owner_id == User.id)

    def save(self, commit=False):
        db.session.add(self)

        if commit:
            db.session.commit()

    @property
    def phid(self):
        if self.placeholder:
            return self.placeholder.phid

        return ''

    @property
    def dhid(self):
        if self.placeholder:
            return self.placeholder.device.devicehub_id

        return ''

    def get_status(self):
        return Severity(self.severity)
