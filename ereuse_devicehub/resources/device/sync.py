from contextlib import suppress
from itertools import groupby
from typing import Iterable, Set

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.exceptions import NeedsId
from ereuse_devicehub.resources.device.models import Component, Computer, Device
from ereuse_devicehub.resources.event.models import Remove
from ereuse_devicehub.resources.tag.model import Tag
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.util import OrderedSet

from teal.db import ResourceNotFound
from teal.marshmallow import ValidationError


class Sync:
    """Synchronizes the device and components with the database."""

    def run(self,
            device: Device,
            components: Iterable[Component] or None) -> (Device, OrderedSet):
        """
        Synchronizes the device and components with the database.

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
                           This method performs Add and Remove events
                           so the device ends up with these components.
                           Components are added / updated accordingly.
                           If this is empty, all components are removed.
                           If this is None, it means that we are not
                           providing info about the components, in which
                           case we keep the already existing components
                           of the device –we don't touch them.
        :return: A tuple of:

                 1. The device from the database (with an ID) whose
                    ``components`` field contain the db algorithm_version
                    of the passed-in components.
                 2. A list of Add / Remove (not yet added to session).
        """
        db_device = self.execute_register(device)
        db_components, events = OrderedSet(), OrderedSet()
        if components is not None:  # We have component info (see above)
            assert isinstance(db_device, Computer)
            blacklist = set()  # type: Set[int]
            not_new_components = set()
            for component in components:
                db_component, is_new = self.execute_register_component(component,
                                                                       blacklist,
                                                                       parent=db_device)
                db_components.add(db_component)
                if not is_new:
                    not_new_components.add(db_component)
            # We only want to perform Add/Remove to not new components
            events = self.add_remove(db_device, not_new_components)
            db_device.components = db_components
        return db_device, events

    def execute_register_component(self,
                                   component: Component,
                                   blacklist: Set[int],
                                   parent: Computer):
        """
        Synchronizes one component to the DB.

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
        try:
            if component.hid:
                db_component = Device.query.filter_by(hid=component.hid).one()
            else:
                # Is there a component similar to ours?
                db_component = component.similar_one(parent, blacklist)
                # We blacklist this component so we
                # ensure we don't get it again for another component
                # with the same physical properties
                blacklist.add(db_component.id)
        except ResourceNotFound:
            db.session.add(component)
            # db.session.flush()
            db_component = component
            is_new = True
        else:
            self.merge(component, db_component)
            is_new = False
        return db_component, is_new

    def execute_register(self, device: Device) -> Device:
        """
        Synchronizes one device to the DB.

        This method tries to get an existing device using the HID
        or one of the tags, and...

        - if it already exists it returns a "local synced algorithm_version"
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
        assert inspect(device).transient, 'Device cannot be already synced from DB'
        assert all(inspect(tag).transient for tag in device.tags), 'Tags cannot be synced from DB'
        if not device.tags and not device.hid:
            # We cannot identify this device
            raise NeedsId()
        db_device = None
        if device.hid:
            with suppress(ResourceNotFound):
                db_device = Device.query.filter_by(hid=device.hid).one()
        try:
            tags = {Tag.query.filter_by(id=tag.id).one() for tag in device.tags}  # type: Set[Tag]
        except ResourceNotFound:
            raise ResourceNotFound('tag you are linking to device {}'.format(device))
        linked_tags = {tag for tag in tags if tag.device_id}  # type: Set[Tag]
        if linked_tags:
            sample_tag = next(iter(linked_tags))
            for tag in linked_tags:
                if tag.device_id != sample_tag.device_id:
                    raise MismatchBetweenTags(tag, sample_tag)  # Linked to different devices
            if db_device:  # Device from hid
                if sample_tag.device_id != db_device.id:  # Device from hid != device from tags
                    raise MismatchBetweenTagsAndHid(db_device.id, db_device.hid)
            else:  # There was no device from hid
                db_device = sample_tag.device
        if db_device:  # Device from hid or tags
            self.merge(device, db_device)
        else:  # Device is new and tags are not linked to a device
            device.tags.clear()  # We don't want to add the transient dummy tags
            db.session.add(device)
            db_device = device
        db_device.tags |= tags  # Union of tags the device had plus the (potentially) new ones
        try:
            db.session.flush()
        except IntegrityError as e:
            # Manage 'one tag per organization' unique constraint
            if 'One tag per organization' in e.args[0]:
                # todo test for this
                id = int(e.args[0][135:e.args[0].index(',', 135)])
                raise ValidationError('The device is already linked to tag {} '
                                      'from the same organization.'.format(id),
                                      field_names=['device.tags'])
            else:
                raise
        assert db_device is not None
        return db_device

    @staticmethod
    def merge(device: Device, db_device: Device):
        """
        Copies the physical properties of the device to the db_device.

        This method mutates db_device.
        """
        for field_name, value in device.physical_properties.items():
            if value is not None:
                setattr(db_device, field_name, value)

    @staticmethod
    def add_remove(device: Computer,
                   components: Set[Component]) -> OrderedSet:
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
        # Note that we create the Remove events before the Add ones
        events = OrderedSet()
        old_components = set(device.components)

        adding = components - old_components
        if adding:
            # For the components we are adding, let's remove them from their old parents
            def g_parent(component: Component) -> Device:
                return component.parent or Computer(id=0)  # Computer with id 0 is our Identity

            for parent, _components in groupby(sorted(adding, key=g_parent), key=g_parent):
                if parent.id != 0:  # Is not Computer Identity
                    events.add(Remove(device=parent, components=OrderedSet(_components)))
        return events


class MismatchBetweenTags(ValidationError):
    def __init__(self,
                 tag: Tag,
                 other_tag: Tag,
                 field_names={'device.tags'}):
        message = '{!r} and {!r} are linked to different devices.'.format(tag, other_tag)
        super().__init__(message, field_names)


class MismatchBetweenTagsAndHid(ValidationError):
    def __init__(self,
                 device_id: int,
                 hid: str,
                 field_names={'device.hid'}):
        message = 'Tags are linked to device {} but hid refers to device {}.'.format(device_id,
                                                                                     hid)
        super().__init__(message, field_names)
