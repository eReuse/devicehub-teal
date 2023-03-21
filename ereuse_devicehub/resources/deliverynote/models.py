import uuid
from datetime import datetime
from typing import Iterable

from boltons import urlutils
from citext import CIText
from flask import g
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.enums import TransferState
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.teal.db import IntEnum, check_range
from ereuse_devicehub.teal.resource import url_for_resource


class Deliverynote(Thing):
    id = db.Column(
        UUID(as_uuid=True), primary_key=True
    )  # uuid is generated on init by default
    document_id = db.Column(CIText(), nullable=False)
    creator_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    creator = db.relationship(User, primaryjoin=creator_id == User.id)
    supplier_email = db.Column(
        CIText(),
        db.ForeignKey(User.email),
        nullable=False,
        default=lambda: g.user.email,
    )
    supplier = db.relationship(
        User, primaryjoin=lambda: Deliverynote.supplier_email == User.email
    )
    receiver_address = db.Column(
        CIText(),
        db.ForeignKey(User.email),
        nullable=False,
        default=lambda: g.user.email,
    )
    receiver = db.relationship(
        User, primaryjoin=lambda: Deliverynote.receiver_address == User.email
    )
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date.comment = 'The date the DeliveryNote initiated'
    amount = db.Column(db.Integer, check_range('amount', min=0, max=100), default=0)
    # The following fields are supposed to be 0:N relationships
    # to SnapshotDelivery entity.
    # At this stage of implementation they will treated as a
    # comma-separated string of the devices expexted/transfered
    expected_devices = db.Column(JSONB, nullable=False)
    # expected_devices = db.Column(db.ARRAY(JSONB, dimensions=1), nullable=False)
    transferred_devices = db.Column(db.ARRAY(db.Integer, dimensions=1), nullable=True)
    transfer_state = db.Column(
        IntEnum(TransferState), default=TransferState.Initial, nullable=False
    )
    transfer_state.comment = TransferState.__doc__
    lot_id = db.Column(UUID(as_uuid=True), db.ForeignKey(Lot.id), nullable=False)
    lot = db.relationship(
        Lot,
        backref=db.backref('deliverynote', uselist=False, lazy=True),
        lazy=True,
        primaryjoin=Lot.id == lot_id,
    )

    def __init__(
        self,
        document_id: str,
        amount: str,
        date,
        supplier_email: str,
        expected_devices: Iterable,
        transfer_state: TransferState,
    ) -> None:
        """Initializes a delivery note"""
        super().__init__(
            id=uuid.uuid4(),
            document_id=document_id,
            amount=amount,
            date=date,
            supplier_email=supplier_email,
            expected_devices=expected_devices,
            transfer_state=transfer_state,
        )

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
        return '<Deliverynote {0.document_id}>'.format(self)
