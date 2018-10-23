from itertools import chain

import inflection
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import aliased

from ereuse_devicehub.db import db
from ereuse_devicehub.resources import search
from ereuse_devicehub.resources.agent.models import Organization
from ereuse_devicehub.resources.device.models import Component, Computer, Device
from ereuse_devicehub.resources.event.models import Event, EventWithMultipleDevices, \
    EventWithOneDevice
from ereuse_devicehub.resources.tag.model import Tag


class DeviceSearch(db.Model):
    """Temporary table that stores full-text device documents.

    It provides methods to auto-run
    """
    device_id = db.Column(db.BigInteger,
                          db.ForeignKey(Device.id, ondelete='CASCADE'),
                          primary_key=True)
    device = db.relationship(Device, primaryjoin=Device.id == device_id)

    properties = db.Column(TSVECTOR,
                           nullable=False,
                           index=db.Index('properties gist',
                                          postgresql_using='gist',
                                          postgresql_concurrently=True))
    tags = db.Column(TSVECTOR, index=db.Index('tags gist',
                                              postgresql_using='gist',
                                              postgresql_concurrently=True))

    __table_args__ = {
        'prefixes': ['UNLOGGED']  # Only for temporal tables, can cause table to empty on turn on
    }

    @classmethod
    def update_modified_devices(cls, session: db.Session):
        """Updates the documents of the devices that are part of a
        modified event, or tag in the passed-in session.

        This method is registered as a SQLAlchemy listener in the
        Devicehub class.
        """
        devices_to_update = set()
        for model in chain(session.new, session.dirty):
            if isinstance(model, Event):
                if isinstance(model, EventWithMultipleDevices):
                    devices_to_update |= model.devices
                elif isinstance(model, EventWithOneDevice):
                    devices_to_update.add(model.device)
                if model.parent:
                    devices_to_update.add(model.parent)
                devices_to_update |= model.components
            elif isinstance(model, Tag) and model.device:
                devices_to_update.add(model.device)

        # this flush is controversial:
        # see https://groups.google.com/forum/#!topic/sqlalchemy/hBzfypgPfYo
        # todo probably should replace it with what the solution says
        session.flush()
        for device in (d for d in devices_to_update if not isinstance(d, Component)):
            cls.set_device_tokens(session, device)

    @classmethod
    def set_all_devices_tokens_if_empty(cls, session: db.Session):
        """Generates the search docs if the table is empty.

        This can happen if Postgres' shut down unexpectedly, as
        it deletes unlogged tables as ours.
        """
        if not DeviceSearch.query.first():
            for device in Device.query:
                if not isinstance(device, Component):
                    cls.set_device_tokens(session, device)

    @classmethod
    def set_device_tokens(cls, session: db.Session, device: Device):
        """(Re)Generates the device search tokens."""
        assert not isinstance(device, Component)

        tokens = [
            (inflection.humanize(device.type), search.Weight.B),
            (Device.model, search.Weight.B),
            (Device.manufacturer, search.Weight.C),
            (Device.serial_number, search.Weight.A)
        ]
        if isinstance(device, Computer):
            Comp = aliased(Component)
            tokens.extend((
                (db.func.string_agg(Comp.model, ' '), search.Weight.C),
                (db.func.string_agg(Comp.manufacturer, ' '), search.Weight.D),
                (db.func.string_agg(Comp.serial_number, ' '), search.Weight.B),
                (db.func.string_agg(Comp.type, ' '), search.Weight.B),
                ('Computer', search.Weight.C),
                ('PC', search.Weight.C),
                (inflection.humanize(device.chassis.name), search.Weight.B),
            ))

        properties = session \
            .query(search.Search.vectorize(*tokens)) \
            .filter(Device.id == device.id)

        if isinstance(device, Computer):
            # Join to components
            properties = properties \
                .outerjoin(Comp, Computer.components) \
                .group_by(Device.id)

        tags = session.query(
            search.Search.vectorize(
                (db.func.string_agg(Tag.id, ' '), search.Weight.A),
                (db.func.string_agg(Tag.secondary, ' '), search.Weight.A),
                (db.func.string_agg(Organization.name, ' '), search.Weight.B)
            )
        ).filter(Tag.device_id == device.id).join(Tag.org)

        # Note that commit flushes later
        # todo see how to get rid of the one_or_none() by embedding those as subqueries
        # I don't like this but I want the 'on_conflict_on_update' thingie
        device_document = dict(properties=properties.one_or_none(), tags=tags.one_or_none())
        insert = postgresql.insert(DeviceSearch.__table__) \
            .values(device_id=device.id, **device_document) \
            .on_conflict_do_update(constraint='device_search_pkey', set_=device_document)
        session.execute(insert)
