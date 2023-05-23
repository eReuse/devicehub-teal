from uuid import uuid4

from citext import CIText
from dateutil.tz import tzutc
from flask import g
from sortedcontainers import SortedSet
from sqlalchemy import BigInteger, Column, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.teal.db import CASCADE_OWN, URL


class Transfer(Thing):
    """
    The transfer is a transfer of possession of devices between
    a user and a code (not system user)
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(CIText(), default='', nullable=False)
    date = Column(db.TIMESTAMP(timezone=True))
    description = Column(CIText(), default='', nullable=True)
    lot_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('lot.id', use_alter=True, name='lot_transfer'),
        nullable=False,
    )
    lot = relationship(
        'Lot',
        backref=backref('transfer', lazy=True, uselist=False, cascade=CASCADE_OWN),
        primaryjoin='Transfer.lot_id == Lot.id',
    )
    user_from_id = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), nullable=True)
    user_from = db.relationship(User, primaryjoin=user_from_id == User.id)
    user_to_id = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), nullable=True)
    user_to = db.relationship(User, primaryjoin=user_to_id == User.id)

    @property
    def closed(self):
        if self.date:
            return True

        return False

    def type_transfer(self):
        if self.user_from == g.user:
            return 'Outgoing'

        if self.user_to == g.user:
            return 'Incoming'

        return 'Temporary'


class DeliveryNote(Thing):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    number = Column(CIText(), default='', nullable=False)
    date = Column(db.TIMESTAMP(timezone=True))
    units = Column(Integer, default=0)
    weight = Column(Integer, default=0)

    transfer_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('transfer.id'),
        nullable=False,
    )
    transfer = relationship(
        'Transfer',
        backref=backref('delivery_note', lazy=True, uselist=False, cascade=CASCADE_OWN),
        primaryjoin='DeliveryNote.transfer_id == Transfer.id',
    )


class ReceiverNote(Thing):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    number = Column(CIText(), default='', nullable=False)
    date = Column(db.TIMESTAMP(timezone=True))
    units = Column(Integer, default=0)
    weight = Column(Integer, default=0)

    transfer_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('transfer.id'),
        nullable=False,
    )
    transfer = relationship(
        'Transfer',
        backref=backref('receiver_note', lazy=True, uselist=False, cascade=CASCADE_OWN),
        primaryjoin='ReceiverNote.transfer_id == Transfer.id',
    )


class TransferCustomerDetails(Thing):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_name = Column(CIText(), nullable=True)
    location = Column(CIText(), nullable=True)
    logo = Column(URL(), nullable=True)

    transfer_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('transfer.id'),
        nullable=False,
    )
    transfer = relationship(
        'Transfer',
        backref=backref(
            'customer_details', lazy=True, uselist=False, cascade=CASCADE_OWN
        ),
        primaryjoin='TransferCustomerDetails.transfer_id == Transfer.id',
    )


_sorted_documents = {
    'order_by': lambda: DeviceDocument.created,
    'collection_class': SortedSet,
}


class DeviceDocument(Thing):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    type = Column(db.CIText(), nullable=True)
    date = Column(db.DateTime, nullable=True)
    id_document = Column(db.CIText(), nullable=True)
    description = Column(db.CIText(), nullable=True)
    owner_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    owner = db.relationship(User, primaryjoin=owner_id == User.id)
    device_id = db.Column(BigInteger, db.ForeignKey('device.id'), nullable=False)
    device = db.relationship(
        'Device',
        primaryjoin='DeviceDocument.device_id == Device.id',
        backref=backref(
            'documents', lazy=True, cascade=CASCADE_OWN, **_sorted_documents
        ),
    )
    file_name = Column(db.CIText(), nullable=True)
    file_hash = Column(db.CIText(), nullable=True)
    url = db.Column(URL(), nullable=True)

    # __table_args__ = (
    # db.Index('document_id', id, postgresql_using='hash'),
    # db.Index('type_doc', type, postgresql_using='hash')
    # )

    def get_url(self) -> str:
        if self.url:
            return self.url.to_text()
        return ''

    def __lt__(self, other):
        return self.created.replace(tzinfo=tzutc()) < other.created.replace(
            tzinfo=tzutc()
        )
