from datetime import datetime, timezone

from ereuse_devicehub.db import db

STR_SIZE = 64
STR_BIG_SIZE = 128
STR_SM_SIZE = 32
STR_XSM_SIZE = 16


class Thing(db.Model):
    """The base class of all Devicehub resources.

    This is a loose copy of
    `schema.org's Thing class <https://schema.org/Thing>`_
    using only needed fields.
    """
    __abstract__ = True
    updated = db.Column(db.TIMESTAMP(timezone=True),
                        nullable=False,
                        index=True,
                        server_default=db.text('CURRENT_TIMESTAMP'))
    updated.comment = """The last time Devicehub recorded a change for 
    this thing.
    """
    created = db.Column(db.TIMESTAMP(timezone=True),
                        nullable=False,
                        index=True,
                        server_default=db.text('CURRENT_TIMESTAMP'))
    created.comment = """When Devicehub created this."""

    def __init__(self, **kwargs) -> None:
        # We need to set 'created' before sqlalchemy inits the class
        # to be able to use sorted containers
        self.created = kwargs.get('created', datetime.now(timezone.utc))
        super().__init__(**kwargs)
