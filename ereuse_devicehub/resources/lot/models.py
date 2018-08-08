import uuid
from datetime import datetime
from typing import Set

from flask import g
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import expression
from sqlalchemy_utils import LtreeType
from sqlalchemy_utils.types.ltree import LQUERY

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.models import STR_SIZE, Thing
from ereuse_devicehub.resources.user.models import User


class Lot(Thing):
    id = db.Column(UUID(as_uuid=True),
                   primary_key=True,
                   server_default=db.text('gen_random_uuid()'))
    name = db.Column(db.Unicode(STR_SIZE), nullable=False)
    closed = db.Column(db.Boolean, default=False, nullable=False)
    closed.comment = """
            A closed lot cannot be modified anymore.
        """
    devices = db.relationship(Device,
                              backref=db.backref('parents', lazy=True, collection_class=set),
                              secondary=lambda: LotDevice.__table__,
                              collection_class=set)

    def __repr__(self) -> str:
        return '<Lot {0.name} devices={0.devices!r}>'.format(self)

    def add_child(self, child: 'Lot'):
        """Adds a child to this lot."""
        Edge.add(self.id, child.id)
        db.session.refresh(self)  # todo is this useful?
        db.session.refresh(child)

    def remove_child(self, child: 'Lot'):
        Edge.delete(self.id, child.id)

    def __contains__(self, child: 'Lot'):
        return Edge.has_lot(self.id, child.id)


class LotDevice(db.Model):
    device_id = db.Column(db.BigInteger, db.ForeignKey(Device.id), primary_key=True)
    lot_id = db.Column(UUID(as_uuid=True), db.ForeignKey(Lot.id), primary_key=True)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    author_id = db.Column(UUID(as_uuid=True),
                          db.ForeignKey(User.id),
                          nullable=False,
                          default=lambda: g.user.id)
    author = db.relationship(User, primaryjoin=author_id == User.id)
    author_id.comment = """
        The user that put the device in the lot.
    """


class Edge(Thing):
    id = db.Column(db.UUID(as_uuid=True),
                   primary_key=True,
                   server_default=db.text('gen_random_uuid()'))
    lot_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey(Lot.id), nullable=False)
    lot = db.relationship(Lot,
                          backref=db.backref('edges', lazy=True, collection_class=set),
                          primaryjoin=Lot.id == lot_id)
    path = db.Column(LtreeType, unique=True, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(path, name='edge_path_unique', deferrable=True, initially='immediate'),
        db.Index('path_gist', path, postgresql_using='gist'),
        db.Index('path_btree', path, postgresql_using='btree')
    )

    def children(self) -> Set['Edge']:
        """Get the children edges."""
        # From https://stackoverflow.com/a/41158890
        exp = '*.{}.*{{1}}'.format(self.lot_id)
        return set(self.query
                   .filter(self.path.lquery(expression.cast(exp, LQUERY)))
                   .distinct(self.__class__.lot_id)
                   .all())

    @classmethod
    def add(cls, parent_id: uuid.UUID, child_id: uuid.UUID):
        """Creates an edge between parent and child."""
        db.session.execute(db.func.add_edge(str(parent_id), str(child_id)))

    @classmethod
    def delete(cls, parent_id: uuid.UUID, child_id: uuid.UUID):
        """Deletes the edge between parent and child."""
        db.session.execute(db.func.delete_edge(str(parent_id), str(child_id)))

    @classmethod
    def has_lot(cls, parent_id: uuid.UUID, child_id: uuid.UUID) -> bool:
        return bool(db.session.execute(
            "SELECT 1 from edge where path ~ '*.{}.*.{}.*'".format(
                str(parent_id).replace('-', '_'), str(child_id).replace('-', '_'))
        ).first())
