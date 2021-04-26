from itertools import chain

import inflection
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import aliased

from ereuse_devicehub.db import db
from ereuse_devicehub.resources import search
from ereuse_devicehub.resources.action.models import Action, ActionWithMultipleDevices, \
    ActionWithOneDevice
from ereuse_devicehub.resources.agent.models import Organization
from ereuse_devicehub.resources.device.models import Component, Computer, Device
from ereuse_devicehub.resources.tag.model import Tag


class DeviceSearch(db.Model):
    """Temporary table that stores full-text device documents.

    It provides methods to auto-run
    """
    device_id = db.Column(db.BigInteger,
                          db.ForeignKey(Device.id, ondelete='CASCADE'),
                          primary_key=True)
    device = db.relationship(Device, primaryjoin=Device.id == device_id)

    properties = db.Column(TSVECTOR, nullable=False)
    tags = db.Column(TSVECTOR)
    devicehub_ids = db.Column(TSVECTOR)

    __table_args__ = (
        # todo to add concurrency this should be commited separately
        #   see https://docs.sqlalchemy.org/en/latest/dialects/postgresql.html#indexes-with-concurrently
        db.Index('properties gist', properties, postgresql_using='gist'),
        db.Index('tags gist', tags, postgresql_using='gist'),
        db.Index('devicehub_ids gist', devicehub_ids, postgresql_using='gist'),
        {
            'prefixes': ['UNLOGGED']
            # Only for temporal tables, can cause table to empty on turn on
        }

    )

    @classmethod
    def update_modified_devices(cls, session: db.Session):
        """Updates the documents of the devices that are part of a
        modified action, or tag in the passed-in session.

        This method is registered as a SQLAlchemy listener in the
        Devicehub class.
        """
        devices_to_update = set()
        for model in chain(session.new, session.dirty):
            if isinstance(model, Action):
                if isinstance(model, ActionWithMultipleDevices):
                    devices_to_update |= model.devices
                elif isinstance(model, ActionWithOneDevice):
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
            cls.regenerate_search_table(session)

    @classmethod
    def regenerate_search_table(cls, session: db.Session):
        """Deletes and re-computes all the search table."""
        DeviceSearch.query.delete()
        for device in Device.query:
            if not isinstance(device, Component):
                cls.set_device_tokens(session, device)

    @classmethod
    def set_device_tokens(cls, session: db.Session, device: Device):
        """(Re)Generates the device search tokens."""
        assert not isinstance(device, Component)

        tokens = [
            (str(device.id), search.Weight.A),
            (inflection.humanize(device.type), search.Weight.B),
            (Device.model, search.Weight.B),
            (Device.manufacturer, search.Weight.C),
            (Device.serial_number, search.Weight.A)
        ]

        if device.manufacturer:
            # todo this has to be done using a dictionary
            manufacturer = device.manufacturer.lower()
            if 'asus' in manufacturer:
                tokens.append(('asus', search.Weight.B))
            if 'hewlett' in manufacturer or 'hp' in manufacturer or 'h.p' in manufacturer:
                tokens.append(('hp', search.Weight.B))
                tokens.append(('h.p', search.Weight.C))
                tokens.append(('hewlett', search.Weight.C))
                tokens.append(('packard', search.Weight.C))

        if isinstance(device, Computer):
            # Aggregate the values of all the components of pc
            Comp = aliased(Component)
            tokens.extend((
                (db.func.string_agg(db.cast(Comp.id, db.TEXT), ' '), search.Weight.D),
                (db.func.string_agg(Comp.model, ' '), search.Weight.C),
                (db.func.string_agg(Comp.manufacturer, ' '), search.Weight.D),
                (db.func.string_agg(Comp.serial_number, ' '), search.Weight.B),
                (db.func.string_agg(Comp.type, ' '), search.Weight.B),
                ('Computer', search.Weight.C),
                ('PC', search.Weight.C),
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

        devicehub_ids = session.query(
            search.Search.vectorize(
                (db.func.string_agg(Device.devicehub_id, ' '), search.Weight.A),
            )
        ).filter(Device.devicehub_id == device.devicehub_id)

        # Note that commit flushes later
        # todo see how to get rid of the one_or_none() by embedding those as subqueries
        # I don't like this but I want the 'on_conflict_on_update' thingie
        device_document = dict(properties=properties.one_or_none(), tags=tags.one_or_none(), devicehub_ids=devicehub_ids.one_or_none())
        insert = postgresql.insert(DeviceSearch.__table__) \
            .values(device_id=device.id, **device_document) \
            .on_conflict_do_update(constraint='device_search_pkey', set_=device_document)
        session.execute(insert)
