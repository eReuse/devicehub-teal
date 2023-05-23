import uuid
from datetime import datetime
from typing import Union

from boltons import urlutils
from citext import CIText
from flask import g
from sqlalchemy import TEXT
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy_utils import LtreeType
from sqlalchemy_utils.types.ltree import LQUERY

from ereuse_devicehub.db import create_view, db, exp, f
from ereuse_devicehub.resources.device.models import Component, Device
from ereuse_devicehub.resources.enums import TransferState
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.teal.db import CASCADE_OWN, IntEnum, UUIDLtree, check_range
from ereuse_devicehub.teal.resource import url_for_resource


class Lot(Thing):
    id = db.Column(
        UUID(as_uuid=True), primary_key=True
    )  # uuid is generated on init by default
    name = db.Column(CIText(), nullable=False)
    description = db.Column(CIText())
    description.comment = """A comment about the lot."""
    closed = db.Column(db.Boolean, default=False, nullable=False)
    closed.comment = """A closed lot cannot be modified anymore."""

    devices = db.relationship(
        Device,
        backref=db.backref('lots', lazy=True, collection_class=set),
        secondary=lambda: LotDevice.__table__,
        lazy=True,
        collection_class=set,
    )
    """The **children** devices that the lot has.

    Note that the lot can have more devices, if they are inside
    descendant lots.
    """
    parents = db.relationship(
        lambda: Lot,
        viewonly=True,
        lazy=True,
        collection_class=set,
        secondary=lambda: LotParent.__table__,
        primaryjoin=lambda: Lot.id == LotParent.child_id,
        secondaryjoin=lambda: LotParent.parent_id == Lot.id,
        cascade='refresh-expire',  # propagate changes outside ORM
        sync_backref=False,
        backref=db.backref(
            'children',
            viewonly=True,
            lazy=True,
            cascade='refresh-expire',
            collection_class=set,
        ),
    )
    """The parent lots."""

    all_devices = db.relationship(
        Device,
        viewonly=True,
        lazy=True,
        collection_class=set,
        secondary=lambda: LotDeviceDescendants.__table__,
        primaryjoin=lambda: Lot.id == LotDeviceDescendants.ancestor_lot_id,
        secondaryjoin=lambda: LotDeviceDescendants.device_id == Device.id,
    )
    """All devices, including components, inside this lot and its
    descendants.
    """
    amount = db.Column(db.Integer, check_range('amount', min=0, max=100), default=0)
    owner_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    owner = db.relationship(User, primaryjoin=owner_id == User.id)
    transfer_state = db.Column(
        IntEnum(TransferState), default=TransferState.Initial, nullable=False
    )
    transfer_state.comment = TransferState.__doc__
    receiver_address = db.Column(
        CIText(),
        db.ForeignKey(User.email),
        nullable=False,
        default=lambda: g.user.email,
    )
    receiver = db.relationship(User, primaryjoin=receiver_address == User.email)

    # __table_args__ = (
    #     {'schema': 'dbtest'},
    # )

    def __init__(
        self, name: str, closed: bool = closed.default.arg, description: str = None
    ) -> None:
        """Initializes a lot
        :param name:
        :param closed:
        """
        super().__init__(
            id=uuid.uuid4(), name=name, closed=closed, description=description
        )
        Path(self)  # Lots have always one edge per default.

    @property
    def type(self) -> str:
        return self.__class__.__name__

    @property
    def url(self) -> urlutils.URL:
        """The URL where to GET this action."""
        return urlutils.URL(url_for_resource(Lot, item_id=self.id))

    @property
    def descendants(self):
        return self.descendantsq(self.id)

    @property
    def is_temporary(self):
        trade = bool(self.trade)
        transfer = bool(self.transfer)
        owner = self.owner == g.user
        return not trade and not transfer and owner

    @property
    def is_incoming(self):
        if self.trade:
            return self.trade.user_to == g.user
        if self.transfer:
            return self.transfer.user_to == g.user

        return False

    @property
    def is_outgoing(self):
        if self.trade:
            return self.trade.user_from == g.user
        if self.transfer:
            return self.transfer.user_from == g.user

        return False

    @property
    def is_shared(self):
        try:
            self.shared
        except Exception:
            self.shared = ShareLot.query.filter_by(
                lot_id=self.id, user_to=g.user
            ).first()

        if self.shared:
            return True
        return False

    @classmethod
    def descendantsq(cls, id):
        _id = UUIDLtree.convert(id)
        return (cls.id == Path.lot_id) & Path.path.lquery(
            exp.cast('*.{}.*'.format(_id), LQUERY)
        )

    @classmethod
    def roots(cls):
        """Gets the lots that are not under any other lot."""
        return cls.query.join(cls.paths).filter(db.func.nlevel(Path.path) == 1)

    def type_transfer(self):
        # Used in reports lots_export.csv
        if not self.transfer:
            return 'Temporary'
        if self.transfer.user_from == g.user:
            return 'Outgoing'
        if self.transfer.user_to == g.user:
            return 'Incoming'
        return ''

    def add_children(self, *children):
        """Add children lots to this lot.

        This operation is highly costly as it forces refreshing
        many models in session.
        """
        for child in children:
            if isinstance(child, Lot):
                Path.add(self.id, child.id)
                db.session.refresh(child)
            else:
                assert isinstance(child, uuid.UUID)
                Path.add(self.id, child)
        # We need to refresh the models involved in this operation
        # outside the session / ORM control so the models
        # that have relationships to this model
        # with the cascade 'refresh-expire' can welcome the changes
        db.session.refresh(self)

    def remove_children(self, *children):
        """Remove children lots from this lot.

        This operation is highly costly as it forces refreshing
        many models in session.
        """
        for child in children:
            if isinstance(child, Lot):
                Path.delete(self.id, child.id)
                db.session.refresh(child)
            else:
                assert isinstance(child, uuid.UUID)
                Path.delete(self.id, child)
        db.session.refresh(self)

    def delete(self):
        """Deletes the lot.

        This method removes the children lots and children
        devices orphan from this lot and then marks this lot
        for deletion.
        """
        self.remove_children(*self.children)
        db.session.delete(self)

    def _refresh_models_with_relationships_to_lots(self):
        session = db.Session.object_session(self)
        for model in session:
            if isinstance(model, (Device, Lot, Path)):
                session.expire(model)

    def __contains__(self, child: Union['Lot', Device]):
        if isinstance(child, Lot):
            return Path.has_lot(self.id, child.id)
        elif isinstance(child, Device):
            device = (
                db.session.query(LotDeviceDescendants)
                .filter(LotDeviceDescendants.device_id == child.id)
                .filter(LotDeviceDescendants.ancestor_lot_id == self.id)
                .one_or_none()
            )
            return device
        else:
            raise TypeError(
                'Lot only contains devices and lots, not {}'.format(child.__class__)
            )

    def __repr__(self) -> str:
        return '<Lot {0.name} devices={0.devices!r}>'.format(self)


class LotDevice(db.Model):
    device_id = db.Column(db.BigInteger, db.ForeignKey(Device.id), primary_key=True)
    lot_id = db.Column(UUID(as_uuid=True), db.ForeignKey(Lot.id), primary_key=True)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    author_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    author = db.relationship(User, primaryjoin=author_id == User.id)
    author_id.comment = """The user that put the device in the lot."""
    device = relationship(
        'Device',
        primaryjoin='Device.id == LotDevice.device_id',
    )


class Path(db.Model):
    id = db.Column(
        db.UUID(as_uuid=True),
        primary_key=True,
        server_default=db.text('gen_random_uuid()'),
    )
    lot_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey(Lot.id), nullable=False)
    lot = db.relationship(
        Lot,
        backref=db.backref(
            'paths', lazy=True, collection_class=set, cascade=CASCADE_OWN
        ),
        primaryjoin=Lot.id == lot_id,
    )
    path = db.Column(LtreeType, nullable=False)
    created = db.Column(
        db.TIMESTAMP(timezone=True), server_default=db.text('CURRENT_TIMESTAMP')
    )
    created.comment = """When Devicehub created this."""

    __table_args__ = (
        # dag.delete_edge needs to disable internally/temporarily the unique constraint
        db.UniqueConstraint(
            path, name='path_unique', deferrable=True, initially='immediate'
        ),
        db.Index('path_gist', path, postgresql_using='gist'),
        db.Index('path_btree', path, postgresql_using='btree'),
        db.Index('lot_id_index', lot_id, postgresql_using='hash'),
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
                "SELECT 1 from path where path ~ '*.{}.*.{}.*'".format(
                    parent_id, child_id
                )
            ).first()
        )


class LotDeviceDescendants(db.Model):
    """A view facilitating querying inclusion between devices and lots,
    including components.

    The view has 4 columns:
    1. The ID of the device.
    2. The ID of a lot containing the device.
    3. The ID of the lot that directly contains the device.
    4. If 1. is a component, the ID of the device that is inside the lot.
    """

    _ancestor = Lot.__table__.alias(name='ancestor')
    """Ancestor lot table."""
    _desc = Lot.__table__.alias()
    """Descendant lot table."""
    lot_device = _desc.join(LotDevice, _desc.c.id == LotDevice.lot_id).join(
        Path, _desc.c.id == Path.lot_id
    )
    """Join: Path -- Lot -- LotDevice"""

    descendants = (
        "path.path ~ (CAST('*.'|| replace(CAST({}.id as text), '-', '_') "
        "|| '.*' AS LQUERY))".format(_ancestor.name)
    )
    """Query that gets the descendants of the ancestor lot."""
    devices = (
        db.select(
            [
                LotDevice.device_id,
                _desc.c.id.label('parent_lot_id'),
                _ancestor.c.id.label('ancestor_lot_id'),
                None,
            ]
        )
        .select_from(_ancestor)
        .select_from(lot_device)
        .where(db.text(descendants))
    )

    # Components
    _parent_device = Device.__table__.alias(name='parent_device')
    """The device that has the access to the lot."""
    lot_device_component = lot_device.join(
        _parent_device, _parent_device.c.id == LotDevice.device_id
    ).join(Component, _parent_device.c.id == Component.parent_id)
    """Join: Path -- Lot -- LotDevice -- ParentDevice (Device) -- Component"""

    components = (
        db.select(
            [
                Component.id.label('device_id'),
                _desc.c.id.label('parent_lot_id'),
                _ancestor.c.id.label('ancestor_lot_id'),
                LotDevice.device_id.label('device_parent_id'),
            ]
        )
        .select_from(_ancestor)
        .select_from(lot_device_component)
        .where(db.text(descendants))
    )

    __table__ = create_view('lot_device_descendants', devices.union(components))


class LotParent(db.Model):
    i = f.index(
        Path.path, db.func.text2ltree(f.replace(exp.cast(Path.lot_id, TEXT), '-', '_'))
    )

    __table__ = create_view(
        'lot_parent',
        db.select(
            [
                Path.lot_id.label('child_id'),
                exp.cast(
                    f.replace(
                        exp.cast(f.subltree(Path.path, i - 1, i), TEXT), '_', '-'
                    ),
                    UUID,
                ).label('parent_id'),
            ]
        )
        .select_from(Path)
        .where(i > 0),
    )


class ShareLot(Thing):
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    lot_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey(Lot.id), nullable=False)
    lot = db.relationship(Lot, primaryjoin=lot_id == Lot.id)
    user_to_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=True,
    )
    user_to = db.relationship(User, primaryjoin=user_to_id == User.id)
