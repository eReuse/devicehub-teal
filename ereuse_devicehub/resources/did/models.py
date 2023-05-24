from citext import CIText
from flask import g
from sortedcontainers import SortedSet
from sqlalchemy import BigInteger, Column, ForeignKey, Sequence, Unicode
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.resources.action.models import ActionStatus, Snapshot
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.models import STR_SM_SIZE, Thing
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.teal.db import CASCADE_OWN

PROOF_ENUM = {
    'Register': 'Register',
    'IssueDPP': 'IssueDPP',
    'proof_of_recycling': 'proof_of_recycling',
    'Erase': 'Erase',
}

_sorted_proofs = {'order_by': lambda: Proof.created, 'collection_class': SortedSet}


class Proof(Thing):
    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)
    id.comment = """The identifier of the device for this database. Used only
                    internally for software; users should not use this."""
    documentId = Column(CIText(), nullable=True)
    documentId.comment = "is the hash of snapshot.json_wb"
    documentSignature = Column(CIText(), nullable=True)
    documentSignature.comment = "is the snapshot.json_wb with the signature of the user"
    timestamp = Column(BigInteger, nullable=False)
    type = Column(Unicode(STR_SM_SIZE), nullable=False)

    issuer_id = Column(
        UUID(as_uuid=True),
        ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    issuer = relationship(
        User,
        backref=backref('issuered_proofs', lazy=True, collection_class=set),
        primaryjoin=User.id == issuer_id,
    )
    issuer_id.comment = """The user that recorded this proof in the system."""
    device_id = Column(BigInteger, ForeignKey(Device.id), nullable=False)
    device = relationship(
        Device,
        backref=backref('proofs', lazy=True, cascade=CASCADE_OWN),
        primaryjoin=Device.id == device_id,
    )

    snapshot_id = Column(UUID(as_uuid=True), ForeignKey(Snapshot.id), nullable=True)
    snapshot = relationship(
        Snapshot,
        backref=backref('proofs', lazy=True),
        collection_class=OrderedSet,
        primaryjoin=Snapshot.id == snapshot_id,
    )

    action_status_id = Column(
        UUID(as_uuid=True), ForeignKey(ActionStatus.id), nullable=True
    )
    action_status = relationship(
        ActionStatus,
        backref=backref('proofs', lazy=True),
        primaryjoin=ActionStatus.id == action_status_id,
    )


class Dpp(Thing):
    """
    Digital PassPort:
        It is a type of proof with some field more.
        Is the official Digital Passport

    """

    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)
    key = Column(CIText(), nullable=False)
    key.comment = "chid:phid, (chid it's in device and phid it's in the snapshot)"
    documentId = Column(CIText(), nullable=True)
    documentId.comment = "is the hash of snapshot.json_wb"
    documentSignature = Column(CIText(), nullable=True)
    documentSignature.comment = "is the snapshot.json_wb with the signature of the user"
    timestamp = Column(BigInteger, nullable=False)

    issuer_id = Column(
        UUID(as_uuid=True),
        ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    issuer = relationship(
        User,
        backref=backref('issuered_dpp', lazy=True, collection_class=set),
        primaryjoin=User.id == issuer_id,
    )
    issuer_id.comment = """The user that recorded this proof in the system."""
    device_id = Column(BigInteger, ForeignKey(Device.id), nullable=False)
    device = relationship(
        Device,
        backref=backref('dpps', lazy=True, cascade=CASCADE_OWN),
        primaryjoin=Device.id == device_id,
    )

    snapshot_id = Column(UUID(as_uuid=True), ForeignKey(Snapshot.id), nullable=False)
    snapshot = relationship(
        Snapshot,
        backref=backref('dpp', lazy=True),
        collection_class=OrderedSet,
        primaryjoin=Snapshot.id == snapshot_id,
    )
