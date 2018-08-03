from typing import Set, Union
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy_utils import Password

from ereuse_devicehub.resources.agent.models import Individual
from ereuse_devicehub.resources.models import Thing


class User(Thing):
    id = ...  # type: Column
    email = ...  # type: Column
    password = ...  # type: Column
    token = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = ...  # type: UUID
        self.email = ...  # type: str
        self.password = ...  # type: Password
        self.individuals = ...  # type: Set[Individual]
        self.token = ...  # type: UUID

    @property
    def individual(self) -> Union[Individual, None]:
        pass
