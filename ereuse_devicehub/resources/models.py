from datetime import datetime

from ereuse_devicehub.db import db

STR_SIZE = 64
STR_BIG_SIZE = 128
STR_SM_SIZE = 32
STR_XSM_SIZE = 16


class Thing(db.Model):
    __abstract__ = True
    updated = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated.comment = """
        When this was last changed.
    """
    created = db.Column(db.DateTime, default=datetime.utcnow)
    created.comment = """
        When Devicehub created this.
    """
