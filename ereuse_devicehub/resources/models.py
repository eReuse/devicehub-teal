from datetime import datetime, timezone

from ereuse_devicehub.db import db

STR_SIZE = 64
STR_BIG_SIZE = 128
STR_SM_SIZE = 32
STR_XSM_SIZE = 16


class Thing(db.Model):
    __abstract__ = True
    # todo make updated to auto-update
    updated = db.Column(db.TIMESTAMP(timezone=True),
                        nullable=False,
                        server_default=db.text('CURRENT_TIMESTAMP'))
    updated.comment = """
        When this was last changed.
    """
    created = db.Column(db.TIMESTAMP(timezone=True),
                        nullable=False,
                        server_default=db.text('CURRENT_TIMESTAMP'))
    created.comment = """
        When Devicehub created this.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if not self.created:
            self.created = datetime.now(timezone.utc)
