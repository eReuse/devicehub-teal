from datetime import datetime
from typing import Set
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.orm import relationship
from sqlalchemy_utils import Ltree

from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.models import Thing


class Lot(Thing):
    id = ...  # type: Column
    name = ...  # type: Column
    closed = ...  # type: Column
    devices = ...  # type: relationship
    paths = ... # type: relationship

    def __init__(self, name: str, closed: bool = closed.default.arg) -> None:
        super().__init__()
        self.id = ...  # type: UUID
        self.name = ...  # type: str
        self.closed = ...  # type: bool
        self.devices = ...  # type: Set[Device]
        self.paths = ...  # type: Set[Path]

    def add_child(self, child: 'Lot'):
        pass

    def remove_child(self, child: 'Lot'):
        pass

    @classmethod
    def roots(cls):
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
