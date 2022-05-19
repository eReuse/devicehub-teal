from citext import CIText
from flask import g
from sqlalchemy import BigInteger, Column, Sequence, SmallInteger
from sqlalchemy.dialects.postgresql import UUID

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import Snapshot
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
        if self.severity:
            return Severity(self.severity)

        return ''

    def get_device(self):
        if self.snapshot:
            return self.snapshot.device.devicehub_id

        return ''
