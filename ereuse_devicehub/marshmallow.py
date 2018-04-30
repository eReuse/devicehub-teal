from marshmallow.fields import missing_

from ereuse_devicehub.db import db
from teal.db import SQLAlchemy
from teal.marshmallow import NestedOn as TealNestedOn


class NestedOn(TealNestedOn):

    def __init__(self, nested, polymorphic_on='type', db: SQLAlchemy = db, default=missing_,
                 exclude=tuple(), only=None, **kwargs):
        super().__init__(nested, polymorphic_on, db, default, exclude, only, **kwargs)
