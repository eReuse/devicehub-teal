from uuid import uuid4

from citext import CIText
from sqlalchemy import Boolean, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship
from teal.db import CASCADE_OWN

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import User


class Transfer(Thing):
    """
    The transfer is a transfer of possession of devices between
    a user and a code (not system user)
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(CIText(), default='', nullable=False)
    closed = Column(Boolean, nullable=False, default=False)
    date = Column(db.TIMESTAMP(timezone=True))
    description = Column(CIText(), default='', nullable=True)
    lot_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('lot.id', use_alter=True, name='lot_trade'),
        nullable=True,
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
