from citext import CIText
from sqlalchemy import BigInteger, Column, Sequence, SmallInteger
from sqlalchemy.dialects.postgresql import UUID

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.enums import Severity
from ereuse_devicehub.resources.models import Thing


class SnapshotErrors(Thing):
    """A Snapshot errors."""

    id = Column(BigInteger, Sequence('snapshot_errors_seq'), primary_key=True)
    description = Column(CIText(), default='', nullable=False)
    severity = Column(SmallInteger, default=Severity.Info, nullable=False)
    snapshot_uuid = Column(UUID(as_uuid=True), nullable=False)

    def save(self, commit=False):
        db.session.add(self)

        if commit:
            db.session.commit()
