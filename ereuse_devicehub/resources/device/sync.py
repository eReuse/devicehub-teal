import copy
import difflib
from itertools import groupby
from typing import Iterable, Set

import yaml
from flask import g
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import Remove
from ereuse_devicehub.resources.device.models import (
    Component,
    Computer,
    DataStorage,
    Device,
    Placeholder,
)
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.teal.db import ResourceNotFound
from ereuse_devicehub.teal.marshmallow import ValidationError

# DEVICES_ALLOW_DUPLICITY = [
#     'RamModule',
#     'Display',
#     'SoundCard',
#     'Battery',
#     'Camera',
#     'GraphicCard',
# ]


class Sync:
    """Synchronizes the device and components with the database."""

    def run(
        self,
        device: Device,
        components: Iterable[Component] or None,
        create_new_device=False,
    ) -> (Device, OrderedSet):
        """Synchronizes the device and components with the database.

        Identifies if the device and components exist in the database
        and updates / inserts them as necessary.

        Passed-in parameters have to be transient, or said differently,
        not-db-synced objects, or otherwise they would end-up being
        added in the session. `Learn more... <http://docs.sqlalchemy.org/
        en/latest/orm/session_state_management.html#quickie-intro-to
        -object-states>`_.

        This performs Add / Remove as necessary.

        :param device: The device to add / update to the database.
        :param components: Components that are inside of the device.
                           This method performs Add and Remove actions
                           so the device ends up with these components.
                           Components are added / updated accordingly.
                           If this is empty, all components are removed.
                           If this is None, it means that we are not
                           providing info about the components, in which
                           case we keep the already existing components
                           of the device –we don't touch them.
        :return: A tuple of:

                 1. The device from the database (with an ID) whose
                    ``components`` field contain the db version
                    of the passed-in components.
                 2. A list of Add / Remove (not yet added to session).
        """
        if components:
            device.components = OrderedSet(components)
            device.set_hid()
            device.components = OrderedSet()
        db_device = self.execute_register(device, create_new_device)

        db_components, actions = OrderedSet(), OrderedSet()
        if components is not None:  # We have component info (see above)
            if not isinstance(db_device, Computer):
                # Until a good reason is given, we synthetically forbid
                # non-computers with components
                raise ValidationError('Only computers can have components.')
            not_new_components = set()
            for component in components:
                db_component, is_new = self.execute_register_component(component)
                db_components.add(db_component)
                if not is_new:
                    not_new_components.add(db_component)
            # We only want to perform Add/Remove to not new components
            actions = self.add_remove(db_device, not_new_components)
            db_device.components = db_components

        self.create_placeholder(db_device)
        return db_device, actions

    def execute_register_component(self, component: Component):
        """Synchronizes one component to the DB.

        This method is a specialization of :meth:`.execute_register`
        but for components that are inside parents.

        This method assumes components don't have tags, and it tries
        to identify a non-hid component by finding a
        :meth:`ereuse_devicehub.resources.device.models.Component.
        similar_one`.

        :param component: The component to sync.
        :param blacklist: A set of components already found by
                          Component.similar_one(). Pass-in an empty Set.
        :param parent: For components, the computer that contains them.
                       Helper used by Component.similar_one().
        :return: A tuple with:
                 - The synced component. See :meth:`.execute_register`
                   for more info.
                 - A flag stating if the device is new or it already
                   existed in the DB.
        """
        assert inspect(component).transient, 'Component should not be synced from DB'
        # if not is a DataStorage, then need build a new one
        if not isinstance(component, DataStorage):
            db.session.add(component)
            is_new = True
            return component, is_new

        db_component = None

        if component.hid:
            db_component = Device.query.filter_by(
                hid=component.hid, owner_id=g.user.id, placeholder=None, active=True
            ).first()
            is_new = False
        if not db_component:
            db.session.add(component)
            db_component = component
            is_new = True
        return db_component, is_new

    def execute_register(self, device: Device, create_new_device=False) -> Device:
        """Synchronizes one device to the DB.

        This method tries to get an existing device using the HID
        or one of the tags, and...

        - if it already exists it returns a "local synced version"
          –the same ``device`` you passed-in but with updated values
          from the database. In this case we do not
          "touch" any of its values on the DB.
        - If it did not exist, a new device is created in the db.

        This method validates that all passed-in tags (``device.tags``),
        if linked, are linked to the same device, ditto for the hid.
        Finally it links the tags with the device.

        If you pass-in a component that is inside a parent, use
        :meth:`.execute_register_component` as it has more specialized
        methods to handle them.

        :param device: The device to synchronize to the DB.
        :raise NeedsId: The device has not any identifier we can use.
                        To still create the device use
                        ``force_creation``.
        :raise DatabaseError: Any other error from the DB.
        :return: The synced device from the db with the tags linked.
        """
        db_device = device.get_from_db()

        if db_device and db_device.allocated:
            raise ResourceNotFound('device is actually allocated {}'.format(device))

        if not db_device or create_new_device:
            device.tags.clear()  # We don't want to add the transient dummy tags
            if create_new_device or device.get_exist_untrusted_device():
                device.user_trusts = False
            db.session.add(device)
            db_device = device
        try:
            db.session.flush()
        except IntegrityError as e:
            # Manage 'one tag per organization' unique constraint
            if 'One tag per organization' in e.args[0]:
                # todo test for this
                id = int(e.args[0][135 : e.args[0].index(',', 135)])  # noqa: E203
                raise ValidationError(
                    'The device is already linked to tag {} '
                    'from the same organization.'.format(id),
                    field_names=['device.tags'],
                )
            else:
                raise
        assert db_device is not None
        return db_device

    @staticmethod
    def create_placeholder(device: Device):
        """If the device is new, we need create automaticaly a new placeholder"""
        if device.binding:
            for c in device.components:
                if c.phid():
                    continue
                c_dict = copy.copy(c.__dict__)
                c_dict.pop('_sa_instance_state')
                c_dict.pop('id', None)
                c_dict.pop('devicehub_id', None)
                c_dict.pop('actions_multiple', None)
                c_dict.pop('actions_one', None)
                c_placeholder = c.__class__(**c_dict)
                c_placeholder.parent = c.parent.binding.device
                c.parent = device
                component_placeholder = Placeholder(
                    device=c_placeholder, binding=c, is_abstract=True
                )
                db.session.add(c_placeholder)
                db.session.add(component_placeholder)
            return

        dict_device = copy.copy(device.__dict__)
        dict_device.pop('_sa_instance_state')
        dict_device.pop('id', None)
        dict_device.pop('devicehub_id', None)
        dict_device.pop('actions_multiple', None)
        dict_device.pop('actions_one', None)
        dict_device.pop('components', None)
        dev_placeholder = device.__class__(**dict_device)
        if hasattr(device, 'components'):
            for c in device.components:
                c_dict = copy.copy(c.__dict__)
                c_dict.pop('_sa_instance_state')
                c_dict.pop('id', None)
                c_dict.pop('devicehub_id', None)
                c_dict.pop('actions_multiple', None)
                c_dict.pop('actions_one', None)
                c_placeholder = c.__class__(**c_dict)
                c_placeholder.parent = dev_placeholder
                c.parent = device
                component_placeholder = Placeholder(
                    device=c_placeholder, binding=c, is_abstract=True
                )
                db.session.add(c_placeholder)
                db.session.add(component_placeholder)

        placeholder = Placeholder(
            device=dev_placeholder, binding=device, is_abstract=True
        )
        db.session.add(dev_placeholder)
        db.session.add(placeholder)

    @staticmethod
    def add_remove(device: Computer, components: Set[Component]) -> OrderedSet:
        """Generates the Add and Remove actions (but doesn't add them to
        session).

        :param device: A device which ``components`` attribute contains
                       the old list of components. The components that
                       are not in ``components`` will be Removed.
        :param components: List of components that are potentially to
                           be Added. Some of them can already exist
                           on the device, in which case they won't
                           be re-added.
        :return: A list of Add / Remove actions.
        """
        # Note that we create the Remove actions before the Add ones
        actions = OrderedSet()
        old_components = set(device.components)

        adding = components - old_components
        if adding:
            # For the components we are adding, let's remove them from their old parents
            def g_parent(component: Component) -> Device:
                return component.parent or Device(
                    id=0
                )  # Computer with id 0 is our Identity

            for parent, _components in groupby(
                sorted(adding, key=g_parent), key=g_parent
            ):
                set_components = OrderedSet(_components)
                check_owners = (x.owner_id == g.user.id for x in set_components)
                # Is not Computer Identity and all components have the correct owner
                if parent.id != 0 and all(check_owners):
                    actions.add(Remove(device=parent, components=set_components))
        return actions


class MismatchBetweenTags(ValidationError):
    def __init__(self, tag: Tag, other_tag: Tag, field_names={'device.tags'}):
        message = '{!r} and {!r} are linked to different devices.'.format(
            tag, other_tag
        )
        super().__init__(message, field_names)


class MismatchBetweenTagsAndHid(ValidationError):
    def __init__(self, device_id: int, hid: str, field_names={'device.hid'}):
        message = 'Tags are linked to device {} but hid refers to device {}.'.format(
            device_id, hid
        )
        super().__init__(message, field_names)


class MismatchBetweenProperties(ValidationError):
    def __init__(self, props1, props2, field_names={'device'}):
        message = 'The device from the tag and the passed-in differ the following way:'
        message += '\n'.join(
            difflib.ndiff(
                yaml.dump(props1).splitlines(), yaml.dump(props2).splitlines()
            )
        )
        super().__init__(message, field_names)
