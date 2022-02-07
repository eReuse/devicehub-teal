import uuid
from typing import List, Set

from sqlalchemy import Column
from sqlalchemy.orm import relationship
from sqlalchemy_utils import PhoneNumber
from teal import enums

from ereuse_devicehub.resources.action.models import Action, Trade
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.resources.user import User


class Agent(Thing):
    id = ...  # type: Column
    name = ...  # type: Column
    tax_id = ...  # type: Column
    country = ...  # type: Column
    telephone = ...  # type: Column
    email = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = ...  # type: uuid.UUID
        self.name = ...  # type: str
        self.tax_id = ...  # type: str
        self.country = ...  # type: enums.Country
        self.telephone = ...  # type: PhoneNumber
        self.email = ...  # type: str
        self.actions_agent = ...  # type: Set[Action] # Ordered
        self.actions_to = ...  # type: Set[Trade] # Ordered

    @property
    def actions(self) -> List[Action]:
        pass


class Organization(Agent):
    def __init__(self, name: str, **kwargs):
        super().__init__(**kwargs)
        self.members = ...  # type: Set[Membership]
        self.tags = ...  # type: Set[Tag]

    @classmethod
    def get_default_org_id(cls) -> uuid.UUID:
        pass


class Individual(Agent):
    member_of = ...  # type:relationship
    active_org_id = ...  # type:Column
    active_org = ...  # type:relationship
    user_id = ...  # type:Column
    user = ...  # type:relationship

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.member_of = ...  # type: Set[Membership]
        self.active_org = ...  # type:  Organization
        self.user = ...  # type: User


class Membership(Thing):
    organization = ...  # type: Column
    individual = ...  # type: Column
    id = ...  # type: Column

    def __init__(self, organization: Organization, individual: Individual, id: str = None) -> None:
        super().__init__()
        self.organization = ...  # type: Organization
        self.individual = ...  # type: Individual
        self.id = ...  # type: str


class Person(Individual):
    pass


class System(Individual):
    pass
