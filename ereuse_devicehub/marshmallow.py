from marshmallow.fields import missing_

from ereuse_devicehub.db import db
from teal.db import SQLAlchemy
from teal.marshmallow import NestedOn as TealNestedOn


class NestedOn(TealNestedOn):
    __doc__ = TealNestedOn.__doc__

    def __init__(self, nested, polymorphic_on='type', db: SQLAlchemy = db, collection_class=list,
                 default=missing_, exclude=tuple(), only=None, **kwargs):
        super().__init__(nested, polymorphic_on, db, collection_class, default, exclude, only,
                         **kwargs)
