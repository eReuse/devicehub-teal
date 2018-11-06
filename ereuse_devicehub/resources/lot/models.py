import uuid
from datetime import datetime

from boltons import urlutils
from citext import CIText
from flask import g
from sqlalchemy import TEXT
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import expression as exp
from sqlalchemy_utils import LtreeType
from sqlalchemy_utils.types.ltree import LQUERY
from teal.db import UUIDLtree
from teal.resource import url_for_resource

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import User


class Lot(Thing):
    id = db.Column(UUID(as_uuid=True), primary_key=True)  # uuid is generated on init by default
    name = db.Column(CIText(), nullable=False)
    description = db.Column(CIText())
    description.comment = """A comment about the lot."""
    closed = db.Column(db.Boolean, default=False, nullable=False)
    closed.comment = """
            A closed lot cannot be modified anymore.
        """
    devices = db.relationship(Device,
                              backref=db.backref('lots', lazy=True, collection_class=set),
                              secondary=lambda: LotDevice.__table__,
                              collection_class=set)
    """
    The **children** devices that the lot has.
    
    Note that the lot can have more devices, if they are inside 
    descendant lots.
    """

    def __init__(self, name: str, closed: bool = closed.default.arg,
                 description: str = None) -> None:
        """
        Initializes a lot
        :param name:
        :param closed:
        """
        super().__init__(id=uuid.uuid4(), name=name, closed=closed, description=description)
        Path(self)  # Lots have always one edge per default.

    def add_child(self, child):
        """Adds a child to this lot."""
        if isinstance(child, Lot):
            Path.add(self.id, child.id)
            db.session.refresh(self)  # todo is this useful?
            db.session.refresh(child)
        else:
            assert isinstance(child, uuid.UUID)
            Path.add(self.id, child)
            db.session.refresh(self)  # todo is this useful?

    def remove_child(self, child):
        if isinstance(child, Lot):
            Path.delete(self.id, child.id)
        else:
            assert isinstance(child, uuid.UUID)
            Path.delete(self.id, child)

    @property
    def url(self) -> urlutils.URL:
        """The URL where to GET this event."""
        return urlutils.URL(url_for_resource(Lot, item_id=self.id))

    @property
    def children(self):
        """The children lots."""
        # From https://stackoverflow.com/a/41158890
        id = UUIDLtree.convert(self.id)
        return self.query \
            .join(self.__class__.paths) \
            .filter(Path.path.lquery(exp.cast('*.{}.*{{1}}'.format(id), LQUERY)))

    @property
    def descendants(self):
        return self.descendantsq(self.id)

    @classmethod
    def descendantsq(cls, id):
        _id = UUIDLtree.convert(id)
        return (cls.id == Path.lot_id) & Path.path.lquery(exp.cast('*.{}.*'.format(_id), LQUERY))

    @property
    def parents(self):
        return self.parentsq(self.id)

    @classmethod
    def parentsq(cls, id: UUID):
        """The parent lots."""
        id = UUIDLtree.convert(id)
        i = db.func.index(Path.path, id)
        parent_id = db.func.replace(exp.cast(db.func.subpath(Path.path, i - 1, i), TEXT), '_', '-')
        join_clause = parent_id == exp.cast(Lot.id, TEXT)
        return cls.query.join(Path, join_clause).filter(
            Path.path.lquery(exp.cast('*{{1}}.{}.*'.format(id), LQUERY))
        )

    @classmethod
    def roots(cls):
        """Gets the lots that are not under any other lot."""
        return cls.query.join(cls.paths).filter(db.func.nlevel(Path.path) == 1)

    def __contains__(self, child: 'Lot'):
        return Path.has_lot(self.id, child.id)

    def __repr__(self) -> str:
        return '<Lot {0.name} devices={0.devices!r}>'.format(self)


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


class Path(db.Model):
    id = db.Column(db.UUID(as_uuid=True),
                   primary_key=True,
                   server_default=db.text('gen_random_uuid()'))
    lot_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey(Lot.id), nullable=False, index=True)
    lot = db.relationship(Lot,
                          backref=db.backref('paths', lazy=True, collection_class=set),
                          primaryjoin=Lot.id == lot_id)
    path = db.Column(LtreeType, nullable=False)
    created = db.Column(db.TIMESTAMP(timezone=True), server_default=db.text('CURRENT_TIMESTAMP'))
    created.comment = """
            When Devicehub created this.
        """

    __table_args__ = (
        # dag.delete_edge needs to disable internally/temporarily the unique constraint
        db.UniqueConstraint(path, name='path_unique', deferrable=True, initially='immediate'),
        db.Index('path_gist', path, postgresql_using='gist'),
        db.Index('path_btree', path, postgresql_using='btree')
    )

    def __init__(self, lot: Lot) -> None:
        super().__init__(lot=lot)
        self.path = UUIDLtree(lot.id)

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
        parent_id = UUIDLtree.convert(parent_id)
        child_id = UUIDLtree.convert(child_id)
        return bool(
            db.session.execute(
                "SELECT 1 from path where path ~ '*.{}.*.{}.*'".format(parent_id, child_id)
            ).first()
        )
