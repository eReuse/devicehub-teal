import copy
from contextlib import suppress

from citext import CIText
from flask import g
from sortedcontainers import SortedSet
from sqlalchemy import BigInteger, Column, Sequence
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.enums import Severity
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.teal.db import CASCADE_OWN, URL

_sorted_documents = {
    'order_by': lambda: TradeDocument.created,
    'collection_class': SortedSet,
}


class TradeDocument(Thing):
    """This represent a document involved in a trade action.
    Every document is added to a lot.
    When this lot is converted in one trade, the action trade is added to the document
    and the action trade need to be confirmed for the both users of the trade.
    This confirmation can be revoked and this revoked need to be ConfirmRevoke for have
    some efect.

    This documents can be invoices or list of devices or certificates of erasure of
    one disk.

    Like a Devices one document have actions and is possible add or delete of one lot
    if this lot don't have a trade

    The document is saved in the database

    """

    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)
    id.comment = """The identifier of the device for this database. Used only
    internally for software; users should not use this.
    """
    # type = Column(Unicode(STR_SM_SIZE), nullable=False)
    date = Column(db.DateTime)
    date.comment = """The date of document, some documents need to have one date
    """
    id_document = Column(CIText())
    id_document.comment = (
        """The id of one document like invoice so they can be linked."""
    )
    description = Column(db.CIText())
    description.comment = """A description of document."""
    owner_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    owner = db.relationship(User, primaryjoin=owner_id == User.id)
    lot_id = db.Column(UUID(as_uuid=True), db.ForeignKey('lot.id'), nullable=False)
    lot = db.relationship(
        'Lot',
        backref=backref(
            'documents', lazy=True, cascade=CASCADE_OWN, **_sorted_documents
        ),
        primaryjoin='TradeDocument.lot_id == Lot.id',
    )
    lot.comment = """Lot to which the document is associated"""
    file_name = Column(db.CIText())
    file_name.comment = """This is the name of the file when user up the document."""
    file_hash = Column(db.CIText())
    file_hash.comment = """This is the hash of the file produced from frontend."""
    url = db.Column(URL())
    url.comment = """This is the url where resides the document."""
    weight = db.Column(db.Float())
    weight.comment = (
        """This is the weight of one container than this document express."""
    )

    __table_args__ = (
        db.Index('document_id', id, postgresql_using='hash'),
        # db.Index('type_doc', type, postgresql_using='hash')
    )

    @property
    def actions(self) -> list:
        """All the actions where the device participated, including:

        1. Actions performed directly to the device.
        2. Actions performed to a component.
        3. Actions performed to a parent device.

        Actions are returned by descending ``created`` time.
        """
        return sorted(self.actions_docs, key=lambda x: x.created)

    @property
    def trading(self):
        """The trading state, or None if no Trade action has
        ever been performed to this device. This extract the posibilities for to do"""

        confirm = 'Confirm'
        need_confirm = 'Need Confirmation'
        double_confirm = 'Document Confirmed'
        revoke = 'Revoke'
        revoke_pending = 'Revoke Pending'
        confirm_revoke = 'Document Revoked'
        ac = self.last_action_trading()
        if not ac:
            return

        if ac.type == 'ConfirmRevokeDocument':
            # can to do revoke_confirmed
            return confirm_revoke

        if ac.type == 'RevokeDocument':
            if ac.user == g.user:
                # can todo revoke_pending
                return revoke_pending
            else:
                # can to do confirm_revoke
                return revoke

        if ac.type == 'ConfirmDocument':
            if ac.user == self.owner:
                if self.owner == g.user:
                    # can to do revoke
                    return confirm
                else:
                    # can to do confirm
                    return need_confirm
            else:
                # can to do revoke
                return double_confirm

    @property
    def total_weight(self):
        """Return all weight than this container have."""
        weight = self.weight or 0
        for x in self.actions:
            if not x.type == 'MoveOnDocument' or not x.weight:
                continue
            if self == x.container_from:
                continue
            weight += x.weight

        return weight

    def get_url(self) -> str:
        if self.url:
            return self.url.to_text()
        return ''

    def last_action_trading(self):
        """which is the last action trading"""
        with suppress(StopIteration, ValueError):
            actions = copy.copy(self.actions)
            actions.sort(key=lambda x: x.created)
            t_trades = [
                'Trade',
                'Confirm',
                'ConfirmRevokeDocument',
                'RevokeDocument',
                'ConfirmDocument',
            ]
            return next(e for e in reversed(actions) if e.t in t_trades)

    def _warning_actions(self, actions):
        """Show warning actions"""
        return sorted(ev for ev in actions if ev.severity >= Severity.Warning)

    def __lt__(self, other):
        if self.id and other.id:
            return self.id < other.id
        return False

    def __str__(self) -> str:
        return '{0.file_name}'.format(self)
