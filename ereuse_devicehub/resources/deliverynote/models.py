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
from ereuse_devicehub.resources.enums import TransferState


class Deliverynote(Thing):
    id = db.Column(UUID(as_uuid=True), primary_key=True)  # uuid is generated on init by default
    documentID = db.Column(CIText(), nullable=False)
    creator_id = Column(Integer, ForeignKey(User.id))
    creator = db.relationship(User, primaryjoin=creator_id == User.id)
    supplier_id = Column(Integer, ForeignKey(User.id))
    supplier = db.relationship(User, primaryjoin=supplier_id == User.id)
    date = db.Column(db.DateTime, nullable=False)
    # deposit = db.Column(db.Integer, check_range('deposit', min=0, max=100), default=0)
    deposit = db.Column(CIText(), nullable=False)
    # The following fiels are supposed to be 0:N relationships
    # to SnapshotDelivery entity.
    # At this stage of implementation they will treated as a
    # comma-separated string of the devices expexted/transfered
    expected_devices = db.Column(CIText(), nullable=False)
    transferred_devices = db.Column(CIText(), nullable=False)
    transfer_state = db.Column(IntEnum(TransferState), default=TransferState.Initial, nullable=False)
    transfer_state.comment = TransferState.__doc__
    lots = db.relationship(Lot,
                           backref=db.backref('deliverynotes', lazy=True, collection_class=set),
                           secondary=lambda: LotDevice.__table__,
                           lazy=True,
                           collection_class=set)

    def __init__(self) -> None:
        """Initializes a delivery note
        """
        super().__init__(id=uuid.uuid4())

    @property
    def type(self) -> str:
        return self.__class__.__name__

    @property
    def url(self) -> urlutils.URL:
        """The URL where to GET this action."""
        return urlutils.URL(url_for_resource(Deliverynote, item_id=self.id))


    # def delete(self):
    #     """Deletes the lot.

    #     This method removes the children lots and children
    #     devices orphan from this lot and then marks this lot
    #     for deletion.
    #     """
    #     self.remove_children(*self.children)
    #     db.session.delete(self)

    # def _refresh_models_with_relationships_to_lots(self):
    #     session = db.Session.object_session(self)
    #     for model in session:
    #         if isinstance(model, (Device, Lot, Path)):
    #             session.expire(model)

    # def __contains__(self, child: Union['Lot', Device]):
    #     if isinstance(child, Lot):
    #         return Path.has_lot(self.id, child.id)
    #     elif isinstance(child, Device):
    #         device = db.session.query(LotDeviceDescendants) \
    #             .filter(LotDeviceDescendants.device_id == child.id) \
    #             .filter(LotDeviceDescendants.ancestor_lot_id == self.id) \
    #             .one_or_none()
    #         return device
    #     else:
    #         raise TypeError('Lot only contains devices and lots, not {}'.format(child.__class__))

    def __repr__(self) -> str:
        # return '<Lot {0.name} devices={0.devices!r}>'.format(self)
        return '<Deliverynote {0.documentID}>'.format(self)


# class LotDevice(db.Model):
#     device_id = db.Column(db.BigInteger, db.ForeignKey(Device.id), primary_key=True)
#     lot_id = db.Column(UUID(as_uuid=True), db.ForeignKey(Lot.id), primary_key=True)
#     created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
#     author_id = db.Column(UUID(as_uuid=True),
#                           db.ForeignKey(User.id),
#                           nullable=False,
#                           default=lambda: g.user.id)
#     author = db.relationship(User, primaryjoin=author_id == User.id)
#     author_id.comment = """The user that put the device in the lot."""
