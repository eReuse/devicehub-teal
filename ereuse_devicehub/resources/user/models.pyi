from typing import Set, Union
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.orm import relationship
from sqlalchemy_utils import Password

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent.models import Individual
from ereuse_devicehub.resources.inventory import Inventory
from ereuse_devicehub.resources.models import Thing


class User(Thing):
    id = ...  # type: Column
    email = ...  # type: Column
    password = ...  # type: Column
    token = ...  # type: Column
    inventories = ...  # type: relationship

    def __init__(self, email: str, password: str = None,
                 inventories: Set[Inventory] = None) -> None:
        super().__init__()
        self.id = ...  # type: UUID
        self.email = ...  # type: str
        self.password = ...  # type: Password
        self.individuals = ...  # type: Set[Individual]
        self.token = ...  # type: UUID
        self.inventories = ...  # type: Set[Inventory]

    @property
    def individual(self) -> Union[Individual, None]:
        pass


class UserInventory(db.Model):
    pass
