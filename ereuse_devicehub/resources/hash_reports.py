"""Hash implementation and save in database 
"""
import hashlib

from citext import CIText
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

from ereuse_devicehub.db import db


class ReportHash(db.Model):
    """Save the hash than is create when one report is download.
    """
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    id.comment = """The identifier of the device for this database. Used only
    internally for software; users should not use this.
    """
    created = db.Column(db.TIMESTAMP(timezone=True),
                        nullable=False,
                        index=True,
                        server_default=db.text('CURRENT_TIMESTAMP'))
    created.comment = """When Devicehub created this."""
    hash3 = db.Column(CIText(), nullable=False)
    hash3.comment = """The normalized name of the hash."""


def insert_hash(bfile, commit=True):
    hash3 = hashlib.sha3_256(bfile).hexdigest()
    db_hash = ReportHash(hash3=hash3)
    db.session.add(db_hash)
    if commit:
        db.session.commit()
        db.session.flush()

    return hash3


def verify_hash(bfile):
    hash3 = hashlib.sha3_256(bfile.read()).hexdigest()
    return ReportHash.query.filter(ReportHash.hash3 == hash3).count()
