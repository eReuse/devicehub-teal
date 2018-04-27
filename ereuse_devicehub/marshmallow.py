from marshmallow.fields import missing_

from ereuse_devicehub.db import db
from teal.db import SQLAlchemy
from teal.marshmallow import NestedOn as TealNestedOn


class NestedOn(TealNestedOn):
    def __init__(self, nested, polymorphic_on='type', default=missing_, exclude=tuple(),
                 only=None, db: SQLAlchemy = db, **kwargs):
        super().__init__(nested, polymorphic_on, default, exclude, only, db, **kwargs)
