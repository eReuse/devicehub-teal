from datetime import datetime, timezone

from flask_sqlalchemy import event

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
    updated = db.Column(
        db.TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
        server_default=db.text('CURRENT_TIMESTAMP'),
    )
    updated.comment = """The last time Devicehub recorded a change for
    this thing.
    """
    created = db.Column(
        db.TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
        server_default=db.text('CURRENT_TIMESTAMP'),
    )
    created.comment = """When Devicehub created this."""

    def __init__(self, **kwargs) -> None:
        # We need to set 'created' before sqlalchemy inits the class
        # to be able to use sorted containers
        self.created = kwargs.get('created', datetime.now(timezone.utc))
        super().__init__(**kwargs)

    def delete(self):
        db.session.delete(self)


def update_object_timestamp(mapper, connection, thing_obj):
    """This function update the stamptime of field updated"""
    thing_obj.updated = datetime.now(timezone.utc)


def listener_reset_field_updated_in_actual_time(thing_obj):
    """This function launch a event than listen like a signal when some object is saved"""
    event.listen(thing_obj, 'before_update', update_object_timestamp, propagate=True)
