import uuid
from datetime import datetime
from typing import Iterable, Optional, Set, Union
from uuid import UUID

from boltons import urlutils
from sqlalchemy import Column
from sqlalchemy.orm import Query, relationship
from sqlalchemy_utils import Ltree

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.models import Thing

LotQuery = Union[Query, Iterable['Lot']]


class Lot(Thing):
    id = ...  # type: Column
    name = ...  # type: Column
    closed = ...  # type: Column
    devices = ...  # type: relationship
    paths = ...  # type: relationship
    description = ...  # type: Column
    all_devices = ...  # type: relationship
    parents = ...  # type: relationship
    amount = ...  # type: Column
    owner_address = ...  # type: Column
    owner = ...  # type: relationship
    transfer_state = ...  # type: Column
    receiver_address = ...  # type: Column
    receiver = ...  # type: relationship

    def __init__(self, name: str, closed: bool = closed.default.arg) -> None:
        super().__init__()
        self.id = ...  # type: UUID
        self.name = ...  # type: str
        self.closed = ...  # type: bool
        self.devices = ...  # type: Set[Device]
        self.paths = ...  # type: Set[Path]
        self.description = ...  # type: str
        self.all_devices = ...  # type: Set[Device]
        self.parents = ...  # type: Set[Lot]
        self.children = ...  # type: Set[Lot]
        self.owner_address = ...  # type: UUID
        self.transfer_state = ...
        self.receiver_address = ...  # type: str

    def add_children(self, *children: Union[Lot, uuid.UUID]):
        pass

    def remove_children(self, *children: Union[Lot, uuid.UUID]):
        pass

    @classmethod
    def roots(cls) -> LotQuery:
        pass

    @property
    def descendants(self) -> LotQuery:
        pass

    @classmethod
    def descendantsq(cls, id) -> LotQuery:
        pass

    @property
    def url(self) -> urlutils.URL:
        pass

    def delete(self):
        pass


class Path:
    id = ...  # type: Column
    lot_id = ...  # type: Column
    lot = ...  # type: relationship
    path = ...  # type: Column
    created = ...  # type: Column

    def __init__(self, lot: Lot) -> None:
        super().__init__()
        self.id = ...  # type: UUID
        self.lot = ...  # type: Lot
        self.path = ...  # type: Ltree
        self.created = ...  # type: datetime

    @classmethod
    def has_lot(cls, id, id1):
        pass

    @classmethod
    def delete(cls, id, id1):
        pass

    @classmethod
    def add(cls, id, id1):
        pass


class LotDeviceDescendants(db.Model):
    device_id = ...  # type: Column
    ancestor_lot_id = ...  # type: Column
    parent_lot_id = ...  # type: Column
    device_parent_id = ...  # type: Column

    def __init__(self) -> None:
        super().__init__()
        self.device_id = ...  # type: int
        self.ancestor_lot_id = ...  # type: UUID
        self.parent_lot_id = ...  # type: UUID
        self.device_parent_id = ...  # type: Optional[int]
