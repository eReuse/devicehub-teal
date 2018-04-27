from datetime import datetime

from sqlalchemy import CheckConstraint

from ereuse_devicehub.db import db

STR_SIZE = 64
STR_BIG_SIZE = 128
STR_SM_SIZE = 32


def check_range(column: str, min=1, max=None) -> CheckConstraint:
    constraint = '>= {}'.format(min) if max is None else 'BETWEEN {} AND {}'.format(min, max)
    return CheckConstraint('{} {}'.format(column, constraint))


class Thing(db.Model):
    __abstract__ = True
    updated = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created = db.Column(db.DateTime, default=datetime.utcnow)
