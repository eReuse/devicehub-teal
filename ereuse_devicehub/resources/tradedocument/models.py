import os

from itertools import chain
from citext import CIText
from flask import current_app as app, g

from sqlalchemy.dialects.postgresql import UUID
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.models import STR_SM_SIZE, Thing, listener_reset_field_updated_in_actual_time

from sqlalchemy import BigInteger, Boolean, Column, Float, ForeignKey, Integer, \
    Sequence, SmallInteger, Unicode, inspect, text
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import ColumnProperty, backref, relationship, validates
from sqlalchemy.util import OrderedSet
from sqlalchemy_utils import ColorType
from teal.db import CASCADE_DEL, POLYMORPHIC_ID, POLYMORPHIC_ON, \
    check_lower, check_range
from teal.resource import url_for_resource

from ereuse_devicehub.resources.utils import hashcode
from ereuse_devicehub.resources.enums import BatteryTechnology, CameraFacing, ComputerChassis, \
    DataStorageInterface, DisplayTech, PrinterTechnology, RamFormat, RamInterface, Severity, TransferState


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
    id_document.comment = """The id of one document like invoice so they can be linked."""
    description = Column(db.CIText())
    description.comment = """A description of document."""
    owner_id = db.Column(UUID(as_uuid=True),
                         db.ForeignKey(User.id),
                         nullable=False,
                         default=lambda: g.user.id)
    owner = db.relationship(User, primaryjoin=owner_id == User.id)
    file_name = Column(db.CIText())
    file_name.comment = """This is the name of the file when user up the document."""
    file_name_disk = Column(db.CIText())
    file_name_disk.comment = """This is the name of the file as devicehub save in server."""

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
        return sorted(self.actions_multiple_docs, key=lambda x: x.created)

    @property
    def path_to_file(self) -> str:
        """The path of one file is defined by the owner, file_name and created time.

        """
        base = app.config['PATH_DOCUMENTS_STORAGE']
        file_name = "{0.date}-{0.filename}".format(self)
        base = os.path.join(base, g.user.email, file_name)
        return sorted(self.actions_multiple_docs, key=lambda x: x.created)

    def last_action_of(self, *types):
        """Gets the last action of the given types.

        :raise LookupError: Device has not an action of the given type.
        """
        try:
            # noinspection PyTypeHints
            actions = self.actions
            actions.sort(key=lambda x: x.created)
            return next(e for e in reversed(actions) if isinstance(e, types))
        except StopIteration:
            raise LookupError('{!r} does not contain actions of types {}.'.format(self, types))

    def _warning_actions(self, actions):
        return sorted(ev for ev in actions if ev.severity >= Severity.Warning)


    def __lt__(self, other):
        return self.id < other.id

    def __str__(self) -> str:
        return '{0.file_name}'.format(self)
