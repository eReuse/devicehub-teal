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

    def __init__(self, name: str, closed: bool = closed.default.arg) -> None:
        super().__init__()
        self.id = ...  # type: UUID
        self.name = ...  # type: str
        self.closed = ...  # type: bool
        self.devices = ...  # type: Set[Device]
        self.paths = ...  # type: Set[Path]
        description = ...  # type: str

    def add_child(self, child: Union[Lot, uuid.UUID]):
        pass

    def remove_child(self, child: Union[Lot, uuid.UUID]):
        pass

    @classmethod
    def roots(cls) -> LotQuery:
        pass

    @property
    def children(self) -> LotQuery:
        pass

    @property
    def descendants(self) -> LotQuery:
        pass

    @classmethod
    def descendantsq(cls, id) -> LotQuery:
        pass

    @property
    def parents(self) -> LotQuery:
        pass

    @classmethod
    def parentsq(cls, id) -> LotQuery:
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
