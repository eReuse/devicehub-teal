from citext import CIText 
from flask import g
from sqlalchemy import BigInteger, Column, Sequence, Unicode, Boolean
from sqlalchemy.dialects.postgresql import UUID
from teal.db import URL
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.models import Thing, STR_SM_SIZE


class Document(Thing):
    """This represent a generic document."""

    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)
    id.comment = """The identifier of the device for this database. Used only
    internally for software; users should not use this.
    """
    type = Column(Unicode(STR_SM_SIZE), nullable=False)
    date = Column(db.DateTime, nullable=True)
    date.comment = """The date of document, some documents need to have one date
    """
    software = Column(CIText(), nullable=False)
    software.comment = """Which software is used"""
    success = Column(Boolean)
    success.comment = """If the erase was success"""
    id_document = Column(CIText(), nullable=False)
    id_document.comment = """The id of one document like invoice so they can be linked."""
    owner_id = db.Column(UUID(as_uuid=True),
                         db.ForeignKey(User.id),
                         nullable=False,
                         default=lambda: g.user.id)
    owner = db.relationship(User, primaryjoin=owner_id == User.id)
    file_name = Column(db.CIText(), nullable=False)
    file_name.comment = """This is the name of the file when user up the document."""
    file_hash = Column(db.CIText(), nullable=False)
    file_hash.comment = """This is the hash of the file produced from frontend."""
    url = db.Column(URL(), nullable=False)
    url.comment = """This is the url where resides the document."""

    def __str__(self) -> str:
        return '{0.file_name}'.format(self)
