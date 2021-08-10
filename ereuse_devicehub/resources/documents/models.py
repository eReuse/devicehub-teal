from flask import g
from citext import CIText 
from sortedcontainers import SortedSet
from sqlalchemy import BigInteger, Column, Sequence, Unicode, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref
from teal.db import CASCADE_OWN, URL

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.models import Thing, STR_SM_SIZE


_sorted_documents = {
    'order_by': lambda: Document.created,
    'collection_class': SortedSet
}


class Document(Thing):
    """This represent a generic document."""

    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)
    id.comment = """The identifier of the device for this database. Used only
    internally for software; users should not use this.
    """
    document_type = Column(Unicode(STR_SM_SIZE), nullable=False)
    date = Column(db.DateTime, nullable=True)
    date.comment = """The date of document, some documents need to have one date
    """
    id_document = Column(CIText(), nullable=True)
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
    url = db.Column(URL(), nullable=True)
    url.comment = """This is the url where resides the document."""

    def __str__(self) -> str:
        return '{0.file_name}'.format(self)


class JoinedTableMixin:
    # noinspection PyMethodParameters
    @declared_attr
    def id(cls):
        return Column(BigInteger, ForeignKey(Document.id), primary_key=True)


class DataWipeDocument(JoinedTableMixin, Document):
    """This represent a generic document."""

    software = Column(CIText(), nullable=True)
    software.comment = """Which software is used"""
    success = Column(Boolean, default=False)
    success.comment = """If the erase was success"""

    def __str__(self) -> str:
        return '{0.file_name}'.format(self)



class RecycleDocument(JoinedTableMixin, Document):
    """Document than proof how any of weight go to recycling."""

    weight = db.Column(db.Float(nullable=True))
    weight.comment = """Weight than go to recycling"""
    trade_document_id = db.Column(db.BigInteger, db.ForeignKey('trade_document.id'))
    trade_document_id.comment = """This is the trade document used for send material to recyle"""
    lot_id = db.Column(UUID(as_uuid=True),
                         db.ForeignKey('lot.id'),
                         nullable=False)
    lot_id.comment = """This lot is the input lot if the material that will then go definitively to recycling"""
    lot = db.relationship('Lot',
                          backref=backref('recycling_documents',
                                          lazy=True,
                                          cascade=CASCADE_OWN,
                                          **_sorted_documents),
                            primaryjoin='RecycleDocument.lot_id == Lot.id')

    def __str__(self) -> str:
        return '{0.file_name}'.format(self)
