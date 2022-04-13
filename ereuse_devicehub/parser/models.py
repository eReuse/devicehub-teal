from citext import CIText
from flask import g
from sqlalchemy import BigInteger, Column, Sequence, SmallInteger
from sqlalchemy.dialects.postgresql import UUID

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.enums import Severity
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import User


class SnapshotErrors(Thing):
    """A Snapshot errors."""

    id = Column(BigInteger, Sequence('snapshot_errors_seq'), primary_key=True)
    description = Column(CIText(), default='', nullable=False)
    wbid = Column(CIText(), nullable=True)
    severity = Column(SmallInteger, default=Severity.Info, nullable=False)
    snapshot_uuid = Column(UUID(as_uuid=True), nullable=False)
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
