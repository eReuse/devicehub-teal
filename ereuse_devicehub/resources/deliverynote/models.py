import uuid
from datetime import datetime
from typing import Union

from boltons import urlutils
from citext import CIText
from flask import g
from sqlalchemy import TEXT, Enum as DBEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy_utils import LtreeType
from sqlalchemy_utils.types.ltree import LQUERY
from teal.db import CASCADE_OWN, UUIDLtree, check_range, IntEnum
from teal.resource import url_for_resource

from ereuse_devicehub.db import create_view, db, exp, f
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.enums import TransferState


class Deliverynote(Thing):
    id = db.Column(UUID(as_uuid=True), primary_key=True)  # uuid is generated on init by default
    document_id = db.Column(CIText(), nullable=False)
    creator_id = db.Column(UUID(as_uuid=True),
                          db.ForeignKey(User.id),
                          nullable=False,
                          default=lambda: g.user.id)
    creator = db.relationship(User, primaryjoin=creator_id == User.id)
    supplier_email = db.Column(CIText(),
                          db.ForeignKey(User.email),
                          nullable=False,
                          default=lambda: g.user.email)
    supplier = db.relationship(User, primaryjoin=lambda: Deliverynote.supplier_email == User.email)
    receiver_address = db.Column(CIText(),
                          db.ForeignKey(User.email))
                          # nullable=False)
    receiver = db.relationship(User, primaryjoin=lambda: Deliverynote.receiver_address== User.email)
    # supplier = db.relationship(User)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date.comment = 'The date the DeliveryNote initiated'
    # deposit = db.Column(db.Integer, check_range('deposit', min=0, max=100), default=0)
    deposit = db.Column(CIText(), nullable=False)
    # The following fiels are supposed to be 0:N relationships
    # to SnapshotDelivery entity.
    # At this stage of implementation they will treated as a
    # comma-separated string of the devices expexted/transfered
    expected_devices = db.Column(CIText(), nullable=False)
    transferred_devices = db.Column(CIText(), nullable=True)
    transfer_state = db.Column(IntEnum(TransferState), default=TransferState.Initial, nullable=False)
    transfer_state.comment = TransferState.__doc__
    ethereum_address = db.Column(CIText(), unique=True, default=None)
    lot_id = db.Column(UUID(as_uuid=True),
                          db.ForeignKey(Lot.id),
                          nullable=False)
    lots = db.relationship(Lot,
                           backref=db.backref('deliverynotes', lazy=True, collection_class=set),
                           lazy=True,
                           primaryjoin=Lot.id == lot_id,
                           collection_class=set)

    def __init__(self, document_id: str, deposit: str, date,
                 supplier_email: str,
                 expected_devices: str) -> None:
        """Initializes a delivery note
        """
        super().__init__(id=uuid.uuid4(),
                         document_id=document_id, deposit=deposit, date=date,
                         supplier_email=supplier_email,
                         expected_devices=expected_devices)

    @property
    def type(self) -> str:
        return self.__class__.__name__

    @property
    def url(self) -> urlutils.URL:
        """The URL where to GET this action."""
        return urlutils.URL(url_for_resource(Deliverynote, item_id=self.id))

    def delete(self):
        """Deletes the deliverynote.

        This method removes the delivery note.
        """
        db.session.delete(self)

    def __repr__(self) -> str:
        return '<Deliverynote {0.documentID}>'.format(self)
