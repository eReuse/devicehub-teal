from sqlalchemy import Column

from teal.db import Model

STR_SIZE = 64
STR_BIG_SIZE = 128
STR_SM_SIZE = 32
STR_XSM_SIZE = 16


class Thing(Model):
    t = ...  # type: str
    type = ...  # type: str
    updated = ...  # type: Column
    created = ...  # type: Column
