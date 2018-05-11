import re
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
            force_creation: bool = False) -> (Device, List[Add or Remove]):
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
                 1. The device from the database (with an ID) whose
                    ``components`` field contain the db version
                    of the passed-in components.
                 2. A list of Add / Remove (not yet added to session).
        """
        db_device, _ = cls.execute_register(device, force_creation=force_creation)
        db_components, events = [], []
        if components is not None:  # We have component info (see above)
            blacklist = set()  # type: Set[int]
            not_new_components = set()
            for component in components:
                db_component, is_new = cls.execute_register(component, blacklist, parent=db_device)
                db_components.append(db_component)
                if not is_new:
                    not_new_components.add(db_component)
            # We only want to perform Add/Remove to not new components
            events = cls.add_remove(db_device, not_new_components)
            db_device.components = db_components
        return db_device, events

    @classmethod
    def execute_register(cls, device: Device,
                         blacklist: Set[int] = None,
                         force_creation: bool = False,
                         parent: Computer = None) -> (Device, bool):
        """
        Synchronizes one device to the DB.

        This method tries to create a device into the database, and
        if it already exists it returns a "local synced version",
        this is the same ``device`` you passed-in but with updated
        values from the database one (like the id value).

        When we say "local" we mean that if, the device existed on the
        database, we do not "touch" any of its values on the DB.

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
        :return: A tuple with:
                 1. A synchronized device with the DB. It can be a new
                   device or an already existing one.
                 2. A flag stating if the device is new or it existed
                    already in the DB.
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
                    return cls.merge(device, db_component), False
            elif not force_creation:
                raise NeedsId()
        try:
            with db.session.begin_nested():
                # Create transaction savepoint to auto-rollback on insertion err
                # Let's try to insert or update
                db.session.add(device)
                db.session.flush()
        except IntegrityError as e:
            if e.orig.diag.sqlstate == UNIQUE_VIOLATION:
                db.session.rollback()
                # This device already exists in the DB
                field, value = re.findall('\(.*?\)', e.orig.diag.message_detail)  # type: str
                field = field.replace('(', '').replace(')', '')
                value = value.replace('(', '').replace(')', '')
                db_device = Device.query.filter(getattr(device.__class__, field) == value).one()
                return cls.merge(device, db_device), False
            else:
                raise e
        else:
            return device, True  # Our device is new

    @classmethod
    def merge(cls, device: Device, db_device: Device):
        """
        Copies the physical properties of the device to the db_device.
        """
        for field_name, value in device.physical_properties.items():
            if value is not None:
                setattr(db_device, field_name, value)
        return db_device

    @classmethod
    def add_remove(cls, device: Device,
                   components: Set[Component]) -> List[Add or Remove]:
        """
        Generates the Add and Remove events (but doesn't add them to
        session).

        :param device: A device which ``components`` attribute contains
                       the old list of components. The components that
                       are not in ``components`` will be Removed.
        :param components: List of components that are potentially to
                           be Added. Some of them can already exist
                           on the device, in which case they won't
                           be re-added.
        :return: A list of Add / Remove events.
        """
        events = []
        old_components = set(device.components)
        adding = components - old_components
        if adding:
            add = Add(device=device, components=list(adding))

            # For the components we are adding, let's remove them from their old parents
            def g_parent(component: Component) -> int:
                return component.parent or Computer(id=0)  # Computer with id 0 is our Identity

            for parent, _components in groupby(sorted(add.components, key=g_parent), key=g_parent):
                if parent.id != 0:
                    events.append(Remove(device=parent, components=list(_components)))
            events.append(add)

        removing = old_components - components
        if removing:
            events.append(Remove(device=device, components=list(removing)))
        return events
