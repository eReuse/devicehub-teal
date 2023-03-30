from uuid import uuid4

from citext import CIText
from flask import g
from sqlalchemy import Column, Integer
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
