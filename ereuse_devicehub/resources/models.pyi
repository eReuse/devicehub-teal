from datetime import datetime

from sqlalchemy import Column, Table
from teal.db import Model

STR_SIZE = 64
STR_BIG_SIZE = 128
STR_SM_SIZE = 32
STR_XSM_SIZE = 16


class Thing(Model):
    __table__ = ...  # type: Table
    t = ...  # type: str
    type = ...  # type: str
    updated = ...  # type: Column
    created = ...  # type: Column

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.updated = ...  # type: datetime
        self.created = ...  # type: datetime
