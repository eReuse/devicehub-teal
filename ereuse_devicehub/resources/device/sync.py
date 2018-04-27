from contextlib import suppress
from itertools import groupby
from typing import Iterable, List, Set

from psycopg2.errorcodes import UNIQUE_VIOLATION
from sqlalchemy.exc import IntegrityError

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.exceptions import NeedsId
from ereuse_devicehub.resources.device.models import Component, Computer, Device
from ereuse_devicehub.resources.event.models import Add, Remove
from teal.db import ResourceNotFound


class Sync:
    """Synchronizes the device and components with the database."""

    @classmethod
    def run(cls, device: Device,
            components: Iterable[Component] or None,
            force_creation: bool = False) -> (Device, List[Component], List[Add or Remove]):
        """
        Synchronizes the device and components with the database.

        Identifies if the device and components exist in the database
        and updates / inserts them as necessary.

        This performs Add / Remove as necessary.
        :param device: The device to add / update to the database.
        :param components: Components that are inside of the device.
                           This method performs Add and Remove events
                           so the device ends up with these components.
                           Components are added / updated accordingly.
                           If this is empty, all components are removed.
                           If this is None, it means that there is
                           no info about components and the already
                           existing components of the device (in case
                           the device already exists) won't be touch.
        :param force_creation: Shall we create the device even if
                               it doesn't generate HID or have an ID?
                               Only for the device param.
        :return: A tuple of:
                 1. The device from the database (with an ID).
                 2. The same passed-in components from the database (with
                    ids).
                 3. A list of Add / Remove (not yet added to session).
        """
        blacklist = set()  # Helper for execute_register()
        db_device = cls.execute_register(device, blacklist, force_creation)
        if id(device) != id(db_device):
            # Did I get another device from db?
            # In such case update the device from db with new stuff
            cls.merge(device, db_device)
        db_components = []
        for component in components:
            db_component = cls.execute_register(component, blacklist, parent=db_device)
            if id(component) != id(db_component):
                cls.merge(component, db_component)
                db_components.append(db_component)
        events = tuple()
        if components is not None:
            # Only perform Add / Remove when
            events = cls.add_remove(db_device, set(db_components))
        return db_device, db_components, events

    @staticmethod
    def execute_register(device: Device,
                         blacklist: Set[int],
                         force_creation: bool = False,
                         parent: Computer = None) -> Device:
        """
        Synchronizes one device to the DB.

        This method tries to update the device in the database if it
        already exists, otherwise it creates a new one.

        :param device: The device to synchronize to the DB.
        :param blacklist: A set of components already found by
                          Component.similar_one(). Pass-in an empty Set.
        :param force_creation: Allow creating a device even if it
                               doesn't generate HID or doesn't have an
                               ID. Only valid for non-components.
                               Usually used when creating non-branded
                               custom computers (as they don't have
                               S/N).
        :param parent: For components, the computer that contains them.
                       Helper used by Component.similar_one().
        :return: A synchronized device with the DB. It can be a new
                 device or an already existing one.
        :raise NeedsId: The device has not any identifier we can use.
                        To still create the device use
                        ``force_creation``.
        :raise DatabaseError: Any other error from the DB.
        """
        # Let's try to create the device
        if not device.hid and not device.id:
            # We won't be able to surely identify this device
            if isinstance(device, Component):
                with suppress(ResourceNotFound):
                    # Is there a component similar to ours?
                    db_component = device.similar_one(parent, blacklist)
                    # We blacklist this component so we
                    # ensure we don't get it again for another component
                    # with the same physical properties
                    blacklist.add(db_component.id)
                    return db_component
            elif not force_creation:
                raise NeedsId()
        db.session.begin_nested()  # Create transaction savepoint to auto-rollback on insertion err
        try:
            # Let's try to insert or update
            db.session.insert(device)
            db.session.flush()
        except IntegrityError as e:
            if e.orig.diag.sqlstate == UNIQUE_VIOLATION:
                # This device already exists in the DB
                field, value = 'az'  # todo get from e.orig.diag
                return Device.query.find(getattr(device.__class__, field) == value).one()
            else:
                raise e
        else:
            return device  # Our device is new

    @classmethod
    def merge(cls, device: Device, db_device: Device):
        """
        Copies the physical properties of the device to the db_device.
        """
        for field, value in device.physical_properties:
            if value is not None:
                setattr(db_device, field.name, value)
        return db_device

    @classmethod
    def add_remove(cls, device: Device,
                   new_components: Set[Component]) -> List[Add or Remove]:
        """
        Generates the Add and Remove events by evaluating the
        differences between the components the
        :param device:
        :param new_components:
        :return:
        """
        old_components = set(device.components)
        add = Add(device=Device, components=list(new_components - old_components))
        events = [
            Remove(device=device, components=list(old_components - new_components)),
            add
        ]

        # For the components we are adding, let's remove them from their old parents
        def get_parent(component: Component):
            return component.parent

        for parent, components in groupby(sorted(add.components, key=get_parent), key=get_parent):
            if parent is not None:
                events.append(Remove(device=parent, components=list(components)))
        return events
