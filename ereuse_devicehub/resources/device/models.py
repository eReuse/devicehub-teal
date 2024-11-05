import copy
import time
import hashlib
import json
import logging
import os
import pathlib
import uuid
from contextlib import suppress
from fractions import Fraction
from itertools import chain
from operator import attrgetter
from typing import Dict, List, Set

from boltons import urlutils
from citext import CIText
from ereuseapi.methods import API
from flask import current_app as app
from flask import g, request, session, url_for
from more_itertools import unique_everseen
from sqlalchemy import BigInteger, Boolean, Column
from sqlalchemy import Enum as DBEnum
from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    Sequence,
    SmallInteger,
    Unicode,
    inspect,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import ColumnProperty, backref, relationship, validates
from sqlalchemy.util import OrderedSet
from sqlalchemy_utils import ColorType
from stdnum import meid

from ereuse_devicehub.db import db
from ereuse_devicehub.ereuse_utils.naming import HID_CONVERSION_DOC
from ereuse_devicehub.resources.device.metrics import Metrics
from ereuse_devicehub.resources.enums import (
    BatteryTechnology,
    CameraFacing,
    ComputerChassis,
    DataStorageInterface,
    DisplayTech,
    PrinterTechnology,
    RamFormat,
    RamInterface,
    Severity,
    TransferState,
)
from ereuse_devicehub.resources.models import (
    STR_SM_SIZE,
    Thing,
    listener_reset_field_updated_in_actual_time,
)
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.utils import hashcode
from ereuse_devicehub.teal.db import (
    CASCADE_DEL,
    POLYMORPHIC_ID,
    POLYMORPHIC_ON,
    URL,
    IntEnum,
    ResourceNotFound,
    check_lower,
    check_range,
)
from ereuse_devicehub.teal.enums import Layouts
from ereuse_devicehub.teal.marshmallow import ValidationError
from ereuse_devicehub.teal.resource import url_for_resource

logger = logging.getLogger(__name__)


def create_code(context):
    _id = Device.query.order_by(Device.id.desc()).first() or 1
    if not _id == 1:
        _id = _id.id + 1
    return hashcode.encode(_id)


def create_phid(context, count=1):
    phid = str(Placeholder.query.filter(Placeholder.owner == g.user).count() + count)
    if (
        Placeholder.query.filter(Placeholder.owner == g.user)
        .filter(Placeholder.phid == phid)
        .count()
    ):
        return create_phid(context, count=count + 1)
    return phid


class Device(Thing):
    """Base class for any type of physical object that can be identified.

    Device partly extends `Schema's IndividualProduct <https
    ://schema.org/IndividualProduct>`_, adapting it to our
    use case.

    A device requires an identification method, ideally a serial number,
    although it can be identified only with tags too. More ideally
    both methods are used.

    Devices can contain ``Components``, which are just a type of device
    (it is a recursive relationship).
    """

    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)
    id.comment = """The identifier of the device for this database. Used only
    internally for software; users should not use this.
    """
    type = Column(Unicode(STR_SM_SIZE), nullable=False)
    hid = Column(Unicode(), check_lower('hid'), unique=False)
    hid.comment = (
        """The Hardware ID (HID) is the ID traceability
    systems use to ID a device globally. This field is auto-generated
    from Devicehub using literal identifiers from the device,
    so it can re-generated *offline*.
    """
        + HID_CONVERSION_DOC
    )
    model = Column(Unicode(), check_lower('model'))
    model.comment = """The model of the device in lower case.

    The model is the unambiguous, as technical as possible, denomination
    for the product. This field, among others, is used to identify
    the product.
    """
    manufacturer = Column(Unicode(), check_lower('manufacturer'))
    manufacturer.comment = """The normalized name of the manufacturer,
    in lower case.

    Although as of now Devicehub does not enforce normalization,
    users can choose a list of normalized manufacturer names
    from the own ``/manufacturers`` REST endpoint.
    """
    serial_number = Column(Unicode(), check_lower('serial_number'))
    serial_number.comment = """The serial number of the device in lower case."""
    part_number = Column(Unicode(), check_lower('part_number'))
    part_number.comment = """The part number of the device in lower case."""
    brand = db.Column(CIText())
    brand.comment = """A naming for consumers. This field can represent
    several models, so it can be ambiguous, and it is not used to
    identify the product.
    """
    generation = db.Column(db.SmallInteger, check_range('generation', 0))
    generation.comment = """The generation of the device."""
    version = db.Column(db.CIText())
    version.comment = """The version code of this device, like v1 or A001."""
    weight = Column(Float(decimal_return_scale=4), check_range('weight', 0.1, 5))
    weight.comment = """The weight of the device in Kg."""
    width = Column(Float(decimal_return_scale=4), check_range('width', 0.1, 5))
    width.comment = """The width of the device in meters."""
    height = Column(Float(decimal_return_scale=4), check_range('height', 0.1, 5))
    height.comment = """The height of the device in meters."""
    depth = Column(Float(decimal_return_scale=4), check_range('depth', 0.1, 5))
    depth.comment = """The depth of the device in meters."""
    color = Column(ColorType)
    color.comment = """The predominant color of the device."""
    production_date = Column(db.DateTime)
    production_date.comment = """The date of production of the device.
    This is timezone naive, as Workbench cannot report this data with timezone information.
    """
    variant = Column(db.CIText())
    variant.comment = """A variant or sub-model of the device."""
    sku = db.Column(db.CIText())
    sku.comment = """The Stock Keeping Unit (SKU), i.e. a
    merchant-specific identifier for a product or service.
    """
    image = db.Column(db.URL)
    image.comment = "An image of the device."

    owner_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    owner = db.relationship(User, primaryjoin=owner_id == User.id)
    allocated = db.Column(Boolean, default=False)
    allocated.comment = "device is allocated or not."
    devicehub_id = db.Column(
        db.CIText(), nullable=True, unique=True, default=create_code
    )
    devicehub_id.comment = "device have a unique code."
    dhid_bk = db.Column(db.CIText(), nullable=True, unique=False)
    phid_bk = db.Column(db.CIText(), nullable=True, unique=False)
    active = db.Column(Boolean, default=True)
    family = db.Column(db.CIText())
    chid = db.Column(db.CIText())

    _NON_PHYSICAL_PROPS = {
        'id',
        'type',
        'created',
        'updated',
        'parent_id',
        'owner_id',
        'hid',
        'production_date',
        'color',  # these are only user-input thus volatile
        'width',
        'height',
        'depth',
        'weight',
        'brand',
        'generation',
        'production_date',
        'variant',
        'version',
        'family',
        'sku',
        'image',
        'allocated',
        'devicehub_id',
        'system_uuid',
        'active',
        'phid_bk',
        'dhid_bk',
        'chid',
        'user_trusts',
        'chassis',
        'transfer_state',
        'receiver_id',
    }

    __table_args__ = (
        db.Index('device_id', id, postgresql_using='hash'),
        db.Index('type_index', type, postgresql_using='hash'),
    )

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self.set_hid()

    @property
    def reverse_actions(self) -> list:
        return reversed(self.actions)

    @property
    def manual_actions(self) -> list:
        mactions = [
            'ActionDevice',
            'Allocate',
            'DataWipe',
            'Deallocate',
            'Management',
            'Prepare',
            'Ready',
            'Recycling',
            'Refurbish',
            'ToPrepare',
            'ToRepair',
            'Use',
        ]
        return [a for a in self.actions if a in mactions]

    @property
    def actions(self) -> list:
        """All the actions where the device participated, including:

        1. Actions performed directly to the device.
        2. Actions performed to a component.
        3. Actions performed to a parent device.

        Actions are returned by descending ``created`` time.
        """
        actions_multiple = copy.copy(self.actions_multiple)
        actions_one = copy.copy(self.actions_one)
        actions = []

        for ac in actions_multiple:
            ac.real_created = ac.actions_device[0].created
            actions.append(ac)

        for ac in actions_one:
            ac.real_created = ac.created
            actions.append(ac)

        return sorted(actions, key=lambda x: x.real_created)

    @property
    def problems(self):
        """Current actions with severity.Warning or higher.

        There can be up to 3 actions: current Snapshot,
        current Physical action, current Trading action.
        """
        from ereuse_devicehub.resources.action.models import Snapshot
        from ereuse_devicehub.resources.device import states

        actions = set()
        with suppress(LookupError, ValueError):
            actions.add(self.last_action_of(Snapshot))
        with suppress(LookupError, ValueError):
            actions.add(self.last_action_of(*states.Physical.actions()))
        with suppress(LookupError, ValueError):
            actions.add(self.last_action_of(*states.Trading.actions()))
        return self._warning_actions(actions)

    @property
    def physical_properties(self) -> Dict[str, object or None]:
        """Fields that describe the physical properties of a device.

        :return A dictionary:
                - Column.
                - Actual value of the column or None.
        """
        # todo ensure to remove materialized values when start using them
        # todo or self.__table__.columns if inspect fails
        return {
            c.key: getattr(self, c.key, None)
            for c in inspect(self.__class__).attrs
            if isinstance(c, ColumnProperty)
            and not getattr(c, 'foreign_keys', None)
            and c.key not in self._NON_PHYSICAL_PROPS
        }

    @property
    def public_properties(self) -> Dict[str, object or None]:
        """Fields that describe the properties of a device than next show
           in the public page.

        :return A dictionary:
                - Column.
                - Actual value of the column or None.
        """
        non_public = ['amount', 'transfer_state', 'receiver_id']
        hide_properties = list(self._NON_PHYSICAL_PROPS) + non_public
        return {
            c.key: getattr(self, c.key, None)
            for c in inspect(self.__class__).attrs
            if isinstance(c, ColumnProperty)
            and not getattr(c, 'foreign_keys', None)
            and c.key not in hide_properties
        }

    @property
    def public_actions(self) -> List[object]:
        """Actions than we want show in public page as traceability log section
        :return a list of actions:
        """
        hide_actions = ['Price', 'EreusePrice']
        actions = [ac for ac in self.actions if ac.t not in hide_actions]
        actions.reverse()
        return actions

    @property
    def public_link(self) -> str:
        host_url = request.host_url.strip('/')
        return "{}{}".format(host_url, self.url.to_text())

    @property
    def chid_link(self) -> str:
        host_url = request.host_url.strip('/')
        url = url_for('did.did', id_dpp=self.chid)
        return "{}{}".format(host_url, url)

    @property
    def url(self) -> urlutils.URL:
        """The URL where to GET this device."""
        return urlutils.URL(url_for_resource(Device, item_id=self.dhid))

    @property
    def rate(self):
        """The last Rate of the device."""
        with suppress(LookupError, ValueError):
            from ereuse_devicehub.resources.action.models import Rate

            return self.last_action_of(Rate)

    @property
    def price(self):
        """The actual Price of the device, or None if no price has
        ever been set."""
        with suppress(LookupError, ValueError):
            from ereuse_devicehub.resources.action.models import Price

            return self.last_action_of(Price)

    @property
    def last_action_trading(self):
        """which is the last action trading"""
        from ereuse_devicehub.resources.device import states

        with suppress(LookupError, ValueError):
            return self.last_action_of(*states.Trading.actions())

    @property
    def allocated_status(self):
        """Show the actual status of device.
        The status depend of one of this 3 actions:
            - Allocate
            - Deallocate
            - InUse (Live register)
        """
        from ereuse_devicehub.resources.device import states

        with suppress(LookupError, ValueError):
            return self.last_action_of(*states.Usage.actions())

    @property
    def physical_status(self):
        """Show the actual status of device for this owner.
        The status depend of one of this 4 actions:
            - ToPrepare
            - Prepare
            - DataWipe
            - ToRepair
            - Ready
        """
        from ereuse_devicehub.resources.device import states

        with suppress(LookupError, ValueError):
            return self.last_action_of(*states.Physical.actions())

    @property
    def status(self):
        """Show the actual status of device for this owner.
        The status depend of one of this 4 actions:
            - Use
            - Refurbish
            - Recycling
            - Management
        """
        from ereuse_devicehub.resources.device import states

        with suppress(LookupError, ValueError):
            return self.last_action_of(*states.Status.actions())

    @property
    def history_status(self):
        """Show the history of the status actions of the device.
        The status depend of one of this 4 actions:
            - Use
            - Refurbish
            - Recycling
            - Management
        """
        from ereuse_devicehub.resources.device import states

        status_actions = [ac.t for ac in states.Status.actions()]
        history = []
        for ac in self.actions:
            if ac.t not in status_actions:
                continue
            if not history:
                history.append(ac)
                continue
            if ac.rol_user == history[-1].rol_user:
                # get only the last action consecutive for the same user
                history = history[:-1] + [ac]
                continue

            history.append(ac)

        return history

    @property
    def sid(self):
        actions = []
        if self.placeholder and self.placeholder.binding:
            actions = [
                x
                for x in self.placeholder.binding.actions
                if x.t == 'Snapshot' and x.sid
            ]
        else:
            actions = [x for x in self.actions if x.t == 'Snapshot' and x.sid]

        if actions:
            return actions[0].sid

    @property
    def tradings(self):
        return {str(x.id): self.trading(x.lot) for x in self.actions if x.t == 'Trade'}

    def trading(self, lot, simple=None):  # noqa: C901
        """The trading state, or None if no Trade action has
        ever been performed to this device. This extract the posibilities for to do.
        This method is performed for show in the web.
        If you need to do one simple and generic response you can put simple=True for that.
        """
        if not hasattr(lot, 'trade'):
            return

        Status = {
            0: 'Trade',
            1: 'Confirm',
            2: 'NeedConfirmation',
            3: 'TradeConfirmed',
            4: 'Revoke',
            5: 'NeedConfirmRevoke',
            6: 'RevokeConfirmed',
        }

        trade = lot.trade
        user_from = trade.user_from
        user_to = trade.user_to
        status = 0
        last_user = None

        if not hasattr(trade, 'acceptances'):
            return Status[status]

        for ac in self.actions:
            if ac.t not in ['Confirm', 'Revoke']:
                continue

            if ac.user not in [user_from, user_to]:
                continue

            if ac.t == 'Confirm' and ac.action == trade:
                if status in [0, 6]:
                    if simple:
                        status = 2
                        continue
                    status = 1
                    last_user = ac.user
                    if ac.user == user_from and user_to == g.user:
                        status = 2
                    if ac.user == user_to and user_from == g.user:
                        status = 2
                    continue

                if status in [1, 2]:
                    if last_user != ac.user:
                        status = 3
                        last_user = ac.user
                    continue

                if status in [4, 5]:
                    status = 3
                    last_user = ac.user
                    continue

            if ac.t == 'Revoke' and ac.action == trade:
                if status == 3:
                    if simple:
                        status = 5
                        continue
                    status = 4
                    last_user = ac.user
                    if ac.user == user_from and user_to == g.user:
                        status = 5
                    if ac.user == user_to and user_from == g.user:
                        status = 5
                    continue

                if status in [4, 5]:
                    if last_user != ac.user:
                        status = 6
                        last_user = ac.user
                    continue

                if status in [1, 2]:
                    status = 6
                    last_user = ac.user
                    continue

        return Status[status]

    @property
    def revoke(self):
        """If the actual trading state is an revoke action, this property show
        the id of that revoke"""
        from ereuse_devicehub.resources.device import states

        with suppress(LookupError, ValueError):
            action = self.last_action_of(*states.Trading.actions())
            if action.type == 'Revoke':
                return action.id

    @property
    def physical(self):
        """The actual physical state, None otherwise."""
        from ereuse_devicehub.resources.device import states

        with suppress(LookupError, ValueError):
            action = self.last_action_of(*states.Physical.actions())
            return states.Physical(action.__class__)

    @property
    def traking(self):
        """The actual traking state, None otherwise."""
        from ereuse_devicehub.resources.device import states

        with suppress(LookupError, ValueError):
            action = self.last_action_of(*states.Traking.actions())
            return states.Traking(action.__class__)

    @property
    def usage(self):
        """The actual usage state, None otherwise."""
        from ereuse_devicehub.resources.device import states

        with suppress(LookupError, ValueError):
            action = self.last_action_of(*states.Usage.actions())
            return states.Usage(action.__class__)

    @property
    def physical_possessor(self):
        """The actual physical possessor or None.

        The physical possessor is the Agent that has physically
        the device. It differs from legal owners, usufructuarees
        or reserves in that the physical possessor does not have
        a legal relation per se with the device, but it is the one
        that has it physically. As an example, a transporter could
        be a physical possessor of a device although it does not
        own it legally.

        Note that there can only be one physical possessor per device,
        and :class:`ereuse_devicehub.resources.action.models.Receive`
        changes it.
        """
        pass
        # TODO @cayop uncomment this lines for link the possessor with the device
        # from ereuse_devicehub.resources.action.models import Receive
        # with suppress(LookupError):
        #     action = self.last_action_of(Receive)
        #     return action.agent_to

    @property
    def working(self):
        """A list of the current tests with warning or errors. A
        device is working if the list is empty.

        This property returns, for the last test performed of each type,
        the one with the worst ``severity`` of them, or ``None`` if no
        test has been executed.
        """
        from ereuse_devicehub.resources.action.models import Test

        current_tests = unique_everseen(
            (e for e in reversed(self.actions) if isinstance(e, Test)),
            key=attrgetter('type'),
        )  # last test of each type
        return self._warning_actions(current_tests)

    @property
    def verbose_name(self):
        type = self.type or ''
        manufacturer = self.manufacturer or ''
        model = self.model or ''
        return f'{type} {manufacturer} {model}'

    @property
    def dhid(self):
        if self.placeholder:
            return self.placeholder.device.devicehub_id
        if self.binding:
            return self.binding.device.devicehub_id
        return self.devicehub_id

    @property
    def my_partner(self):
        if self.placeholder and self.placeholder.binding:
            return self.placeholder.binding
        if self.binding:
            return self.binding.device
        return self

    @property
    def get_updated(self):
        if self.placeholder and self.placeholder.binding:
            return max([self.updated, self.placeholder.binding.updated])
        if self.binding:
            return max([self.updated, self.binding.device.updated])
        return self.updated

    @declared_attr
    def __mapper_args__(cls):
        """Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.t}
        if cls.t == 'Device':
            args[POLYMORPHIC_ON] = cls.type
        return args

    def get_lots_for_template(self):
        if self.binding:
            return self.binding.device.get_lots_for_template()

        if not self.lots and hasattr(self, 'parent') and self.parent:
            return self.parent.get_lots_for_template()

        lots = []
        for lot in self.lots:
            if lot.is_incoming:
                name = "IN - " + lot.name
                lots.append(name)
            if lot.is_outgoing:
                name = "OUT - " + lot.name
                lots.append(name)
            if lot.is_temporary:
                name = "TEMP - " + lot.name
                lots.append(name)
        lots.sort()
        return lots

    def phid(self):
        if self.placeholder:
            return self.placeholder.phid
        if self.binding:
            return self.binding.phid
        return ''

    def list_tags(self):
        return ', '.join([t.id for t in self.tags])

    def appearance(self):
        actions = copy.copy(self.actions)
        actions.sort(key=lambda x: x.created)
        with suppress(LookupError, ValueError, StopIteration):
            action = next(e for e in reversed(actions) if e.type == 'VisualTest')
            return action.appearance_range

    def functionality(self):
        actions = copy.copy(self.actions)
        actions.sort(key=lambda x: x.created)
        with suppress(LookupError, ValueError, StopIteration):
            action = next(e for e in reversed(actions) if e.type == 'VisualTest')
            return action.functionality_range

    def set_appearance(self, value):
        actions = copy.copy(self.actions)
        actions.sort(key=lambda x: x.created)
        with suppress(LookupError, ValueError, StopIteration):
            action = next(e for e in reversed(actions) if e.type == 'VisualTest')
            action.appearance_range = value

    def set_functionality(self, value):
        actions = copy.copy(self.actions)
        actions.sort(key=lambda x: x.created)
        with suppress(LookupError, ValueError, StopIteration):
            action = next(e for e in reversed(actions) if e.type == 'VisualTest')
            action.functionality_range = value

    def is_abstract(self):
        if self.placeholder:
            if self.placeholder.is_abstract:
                return 'Snapshot'
            if self.placeholder.binding:
                return 'Twin'
            return 'Placeholder'
        if self.binding:
            if self.binding.is_abstract:
                return 'Snapshot'
            return 'Twin'

        return ''

    def get_lots_from_type(self, lot_type):
        lots_type = {
            'temporary': lambda x: x.is_temporary,
            'incoming': lambda x: x.is_incoming,
            'outgoing': lambda x: x.is_outgoing,
        }

        if lot_type not in lots_type:
            return ''

        get_lots_type = lots_type[lot_type]

        lots = self.lots
        if not lots and self.binding:
            lots = self.binding.device.lots

        if lots:
            lots = [lot.name for lot in lots if get_lots_type(lot)]
            return ", ".join(sorted(lots))

        return ''

    def is_status(self, action):
        from ereuse_devicehub.resources.device import states

        if action.type in states.Usage.__members__:
            return "Allocate State: "

        if action.type in states.Status.__members__:
            return "Lifecycle State: "

        if action.type in states.Physical.__members__:
            return "Physical State: "

        return ""

    def get_exist_untrusted_device(self):
        if isinstance(self, Computer):
            if not self.system_uuid:
                return True

            return (
                Computer.query.filter_by(
                    hid=self.hid,
                    user_trusts=False,
                    owner_id=g.user.id,
                    active=True,
                    placeholder=None,
                ).first()
                or False
            )

        return False

    def get_from_db(self):
        if 'property_hid' in app.blueprints.keys():
            try:
                from ereuse_devicehub.modules.device.utils import get_from_db

                return get_from_db(self)
            except Exception:
                pass

        if not self.hid:
            return

        return Device.query.filter_by(
            hid=self.hid,
            owner_id=g.user.id,
            active=True,
            placeholder=None,
        ).first()

    def set_hid(self):
        is_component = isinstance(self, Component)
        if 'property_hid' in app.blueprints.keys() and not is_component:
            try:
                from ereuse_devicehub.modules.device.utils import set_hid

                self.hid = set_hid(self)
                self.set_chid()
                return
            except Exception as err:
                logger.error(err)

        self.hid = "{}-{}-{}-{}".format(
            self._clean_string(self.type),
            self._clean_string(self.manufacturer),
            self._clean_string(self.model),
            self._clean_string(self.serial_number),
        ).lower()
        self.set_chid()

    def _clean_string(self, s):
        if not s:
            return ''
        return s.replace(' ', '_')

    def set_chid(self):
        if self.hid:
            self.chid = hashlib.sha3_256(self.hid.encode()).hexdigest()

    def last_action_of(self, *types):
        """Gets the last action of the given types.

        :raise LookupError: Device has not an action of the given type.
        """
        try:
            # noinspection PyTypeHints
            actions = copy.copy(self.actions)
            actions.sort(key=lambda x: x.created)
            return next(e for e in reversed(actions) if isinstance(e, types))
        except StopIteration:
            raise LookupError(
                '{!r} does not contain actions of types {}.'.format(self, types)
            )

    def which_user_put_this_device_in_trace(self):
        """which is the user than put this device in this trade"""
        actions = copy.copy(self.actions)
        actions.reverse()
        # search the automatic Confirm
        for ac in actions:
            if ac.type == 'Trade':
                action_device = [x for x in ac.actions_device if x.device == self][0]
                if action_device.author:
                    return action_device.author

                return ac.author

    def change_owner(self, new_user):
        """util for change the owner one device"""
        if not new_user:
            return
        self.owner = new_user
        if hasattr(self, 'components'):
            for c in self.components:
                c.owner = new_user

    def reset_owner(self):
        """Change the owner with the user put the device into the trade"""
        user = self.which_user_put_this_device_in_trace()
        self.change_owner(user)

    def _warning_actions(self, actions):
        return sorted(ev for ev in actions if ev.severity >= Severity.Warning)

    def get_metrics(self):
        """
        This method get a list of values for calculate a metrics from a spreadsheet
        """
        metrics = Metrics(device=self)
        return metrics.get_metrics()

    def get_type_logo(self):
        # This is used for see one logo of type of device in the frontend
        types = {
            "Desktop": "bi bi-file-post-fill",
            "Laptop": "bi bi-laptop",
            "Server": "bi bi-server",
            "Processor": "bi bi-cpu",
            "RamModule": "bi bi-list",
            "Motherboard": "bi bi-cpu-fill",
            "NetworkAdapter": "bi bi-hdd-network",
            "GraphicCard": "bi bi-brush",
            "SoundCard": "bi bi-volume-up-fill",
            "Monitor": "bi bi-display",
            "Display": "bi bi-display",
            "ComputerMonitor": "bi bi-display",
            "TelevisionSet": "bi bi-easel",
            "TV": "bi bi-easel",
            "Projector": "bi bi-camera-video",
            "Tablet": "bi bi-tablet-landscape",
            "Smartphone": "bi bi-phone",
            "Cellphone": "bi bi-telephone",
            "HardDrive": "bi bi-hdd-stack",
            "SolidStateDrive": "bi bi-hdd",
        }
        return types.get(self.type, '')

    def connect_api(self):
        if 'dpp' not in app.blueprints.keys() or not self.hid:
            return

        if not session.get('token_dlt'):
            return

        token_dlt = session.get('token_dlt')
        api_dlt = app.config.get('API_DLT')
        if not token_dlt or not api_dlt:
            return

        return API(api_dlt, token_dlt, "ethereum")

    def register_dlt(self):
        if not app.config.get('ID_FEDERATED'):
            return

        api = self.connect_api()
        if not api:
            return

        snapshot = [x for x in self.actions if x.t == 'Snapshot']
        if not snapshot:
            return
        snapshot = snapshot[0]
        from ereuse_devicehub.modules.dpp.models import ALGORITHM
        from ereuse_devicehub.resources.enums import StatusCode
        cny_a = 1
        while cny_a:
            result = api.register_device(
                self.chid,
                ALGORITHM,
                snapshot.phid_dpp,
                app.config.get('ID_FEDERATED')
            )
            try:
                assert result['Status'] == StatusCode.Success.value
                assert result['Data']['data']['timestamp']
                cny_a = 0
            except Exception:
                if result.get("Data") != "Device already exists":
                    logger.error("API return: %s", result)
                    time.sleep(10)

        self.register_proof(result)

        if app.config.get('ID_FEDERATED'):
            cny = 1
            while cny:
                try:
                    api.add_service(
                        self.chid,
                        'DeviceHub',
                        app.config.get('ID_FEDERATED'),
                        'Inventory service',
                        'Inv',
                    )
                    cny = 0
                except Exception:
                    time.sleep(10)

    def register_proof(self, result):
        from ereuse_devicehub.modules.dpp.models import PROOF_ENUM, Proof
        from ereuse_devicehub.resources.enums import StatusCode

        if result['Status'] == StatusCode.Success.value:
            timestamp = result.get('Data', {}).get('data', {}).get('timestamp')

            if not timestamp:
                return

            snapshot = [x for x in self.actions if x.t == 'Snapshot']
            if not snapshot:
                return
            snapshot = snapshot[0]

            d = {
                "type": PROOF_ENUM['Register'],
                "device": self,
                "action": snapshot,
                "timestamp": timestamp,
                "issuer_id": g.user.id,
                "documentId": snapshot.id,
                "documentSignature": snapshot.phid_dpp,
                "normalizeDoc": snapshot.json_hw,
            }
            proof = Proof(**d)
            db.session.add(proof)

        if not hasattr(self, 'components'):
            return

        for c in self.components:
            if isinstance(c, DataStorage):
                c.register_dlt()

    def unreliable(self):
        self.user_trusts = False
        i = 0
        snapshot1 = None
        snapshots = {}

        for ac in self.actions:
            if ac.type == 'Snapshot':
                if i == 0:
                    snapshot1 = ac
                if i > 0:
                    snapshots[ac] = self.get_snapshot_file(ac)
                i += 1

        if not snapshot1:
            return

        self.create_new_device(snapshots.values(), user_trusts=self.user_trusts)
        self.remove_snapshot(snapshots.keys())

        return

    def get_snapshot_file(self, action):
        uuid = action.uuid
        user = g.user.email
        name_file = f"*_{user}_{uuid}.json"
        tmp_snapshots = app.config['TMP_SNAPSHOTS']
        path_dir_base = os.path.join(tmp_snapshots, user)

        for _file in pathlib.Path(path_dir_base).glob(name_file):
            with open(_file) as file_snapshot:
                snapshot = file_snapshot.read()
                return json.loads(snapshot)

    def create_new_device(self, snapshots, user_trusts=True):
        from ereuse_devicehub.inventory.forms import UploadSnapshotForm

        new_snapshots = []
        for snapshot in snapshots:
            snapshot['uuid'] = str(uuid.uuid4())
            filename = "{}.json".format(snapshot['uuid'])
            new_snapshots.append((filename, snapshot))

        form = UploadSnapshotForm()
        form.result = {}
        form.snapshots = new_snapshots
        form.create_new_devices = True
        form.save(commit=False, user_trusts=user_trusts)

    def remove_snapshot(self, snapshots):
        from ereuse_devicehub.parser.models import SnapshotsLog

        for ac in snapshots:
            for slog in SnapshotsLog.query.filter_by(snapshot=ac):
                slog.snapshot_id = None
                slog.snapshot_uuid = None
            db.session.delete(ac)

    def remove_devices(self, devices):
        from ereuse_devicehub.parser.models import SnapshotsLog

        for dev in devices:
            for ac in dev.actions:
                if ac.type != 'Snapshot':
                    continue
                for slog in SnapshotsLog.query.filter_by(snapshot=ac):
                    slog.snapshot_id = None
                    slog.snapshot_uuid = None

            for c in dev.components:
                c.parent_id = None

            for tag in dev.tags:
                tag.device_id = None

            placeholder = dev.binding or dev.placeholder
            if placeholder:
                db.session.delete(placeholder.binding)
                db.session.delete(placeholder.device)
                db.session.delete(placeholder)

    def reliable(self):
        computers = Computer.query.filter_by(
            hid=self.hid,
            owner_id=g.user.id,
            active=True,
            placeholder=None,
        ).order_by(Device.created.asc())

        i = 0
        computer1 = None
        computers_to_remove = []
        for d in computers:
            if i == 0:
                d.user_trusts = True
                computer1 = d
                i += 1
                continue

            computers_to_remove.append(d)

        self.remove_devices(computers_to_remove)
        if not computer1:
            return

        snapshot1 = None
        for ac in computer1.actions_one:
            if ac.type == 'Snapshot':
                snapshot1 = ac
                break

        if not snapshot1:
            return

        return

    def get_last_incoming_lot(self):
        lots = list(self.lots)
        if hasattr(self, "orphan") and self.orphan:
            lots = list(self.lots)
            if self.binding:
                lots = list(self.binding.device.lots)

        elif hasattr(self, "parent") and self.parent:
            lots = list(self.parent.lots)
            if self.parent.binding:
                lots = list(self.parent.binding.device.lots)

        lots = sorted(lots, key=lambda x: x.created)
        lots.reverse()
        for lot in lots:
            if lot.is_incoming:
                return lot
        return None

    def is_mobile(self):
        return isinstance(self, Mobile)

    def __lt__(self, other):
        return self.id < other.id

    def __str__(self) -> str:
        return '{0.t} {0.id}: model {0.model}, S/N {0.serial_number}'.format(self)

    def __format__(self, format_spec):
        if not format_spec:
            return super().__format__(format_spec)
        v = ''
        if 't' in format_spec:
            v += '{0.t} {0.model}'.format(self)
        if 's' in format_spec:
            superclass = self.__class__.mro()[1]
            if not isinstance(self, Device) and superclass != Device:
                assert issubclass(superclass, Thing)
                v += superclass.__name__ + ' '
            v += '{0.manufacturer}'.format(self)
            if self.serial_number:
                v += ' ' + self.serial_number.upper()
        return v


class DisplayMixin:
    """Base class for the Display Component and the Monitor Device."""

    size = Column(
        Float(decimal_return_scale=1), check_range('size', 2, 150), nullable=True
    )
    size.comment = """The size of the monitor in inches."""
    technology = Column(DBEnum(DisplayTech))
    technology.comment = """The technology the monitor uses to display
    the image.
    """
    resolution_width = Column(
        SmallInteger, check_range('resolution_width', 10, 20000), nullable=True
    )
    resolution_width.comment = """The maximum horizontal resolution the
    monitor can natively support in pixels.
    """
    resolution_height = Column(
        SmallInteger, check_range('resolution_height', 10, 20000), nullable=True
    )
    resolution_height.comment = """The maximum vertical resolution the
    monitor can natively support in pixels.
    """
    refresh_rate = Column(SmallInteger, check_range('refresh_rate', 10, 1000))
    contrast_ratio = Column(SmallInteger, check_range('contrast_ratio', 100, 100000))
    touchable = Column(Boolean)
    touchable.comment = """Whether it is a touchscreen."""

    @hybrid_property
    def aspect_ratio(self):
        """The aspect ratio of the display, as a fraction: ``X/Y``.

        Regular values are ``4/3``, ``5/4``, ``16/9``, ``21/9``,
        ``14/10``, ``19/10``, ``16/10``.
        """
        if self.resolution_height and self.resolution_width:
            return Fraction(self.resolution_width, self.resolution_height)
        return 0

    # noinspection PyUnresolvedReferences
    @aspect_ratio.expression
    def aspect_ratio(cls):
        # The aspect ratio to use as SQL in the DB
        # This allows comparing resolutions
        return db.func.round(cls.resolution_width / cls.resolution_height, 2)

    @hybrid_property
    def widescreen(self):
        """Whether the monitor is considered to be widescreen.

        Widescreen monitors are those having a higher aspect ratio
        greater than 4/3.
        """
        # We add a tiny extra to 4/3 to avoid precision errors
        return self.aspect_ratio > 4.001 / 3

    def __str__(self) -> str:
        if self.size:
            return '{0.t} {0.serial_number} {0.size}in ({0.aspect_ratio}) {0.technology}'.format(
                self
            )
        return '{0.t} {0.serial_number} 0in ({0.aspect_ratio}) {0.technology}'.format(
            self
        )

    def __format__(self, format_spec: str) -> str:
        v = ''
        if 't' in format_spec:
            v += '{0.t} {0.model}'.format(self)
        if 's' in format_spec:
            v += '({0.manufacturer}) S/N {0.serial_number}'.format(self)
            if self.size:
                v += '– {0.size}in ({0.aspect_ratio}) {0.technology}'.format(self)
            else:
                v += '– 0in ({0.aspect_ratio}) {0.technology}'.format(self)
        return v


class Placeholder(Thing):
    id = Column(BigInteger, Sequence('placeholder_seq'), primary_key=True)
    phid = Column(Unicode(), nullable=False, default=create_phid)
    pallet = Column(Unicode(), nullable=True)
    pallet.comment = "used for identification where from where is this placeholders"
    info = db.Column(CIText())
    components = Column(CIText())
    info.comment = "more info of placeholders"
    is_abstract = db.Column(Boolean, default=False)
    id_device_supplier = db.Column(CIText())
    id_device_supplier.comment = (
        "Identification used for one supplier of one placeholders"
    )
    id_device_internal = db.Column(CIText())
    id_device_internal.comment = "Identification used internaly for the user"
    kangaroo = db.Column(Boolean, default=False, nullable=True)

    device_id = db.Column(
        BigInteger,
        db.ForeignKey(Device.id),
        nullable=False,
    )
    device = db.relationship(
        Device,
        backref=backref(
            'placeholder', lazy=True, cascade="all, delete-orphan", uselist=False
        ),
        primaryjoin=device_id == Device.id,
    )
    device_id.comment = "datas of the placeholder"

    binding_id = db.Column(
        BigInteger,
        db.ForeignKey(Device.id),
        nullable=True,
    )
    binding = db.relationship(
        Device,
        backref=backref('binding', lazy=True, uselist=False),
        primaryjoin=binding_id == Device.id,
    )
    binding_id.comment = "binding placeholder with workbench device"
    owner_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    owner = db.relationship(User, primaryjoin=owner_id == User.id)

    @property
    def actions(self):
        actions = list(self.device.actions) or []

        if self.binding:
            actions.extend(list(self.binding.actions))

        actions = sorted(actions, key=lambda x: x.created)
        actions.reverse()
        return actions

    @property
    def status(self):
        if self.is_abstract:
            return 'Snapshot'
        if self.binding:
            return 'Twin'
        return 'Placeholder'

    @property
    def documents(self):
        docs = self.device.documents
        if self.binding:
            return docs.union(self.binding.documents)
        return docs

    @property
    def proofs(self):
        proofs = [p for p in self.device.proofs]
        if self.binding:
            proofs.extend([p for p in self.binding.proofs])
        proofs.sort(key=lambda x: x.created, reverse=True)
        return proofs


class Computer(Device):
    """A chassis with components inside that can be processed
    automatically with Workbench Computer.

    Computer is broa extended by ``Desktop``, ``Laptop``, and
    ``Server``. The property ``chassis`` defines it more granularly.
    """

    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    chassis = Column(DBEnum(ComputerChassis), nullable=True)
    chassis.comment = """The physical form of the computer.

    It is a subset of the Linux definition of DMI / DMI decode.
    """
    amount = Column(Integer, check_range('amount', min=0, max=100), default=0)
    owner_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(User.id),
        nullable=False,
        default=lambda: g.user.id,
    )
    # author = db.relationship(User, primaryjoin=owner_id == User.id)
    transfer_state = db.Column(
        IntEnum(TransferState), default=TransferState.Initial, nullable=False
    )
    transfer_state.comment = TransferState.__doc__
    receiver_id = db.Column(UUID(as_uuid=True), db.ForeignKey(User.id), nullable=True)
    receiver = db.relationship(User, primaryjoin=receiver_id == User.id)
    system_uuid = db.Column(UUID(as_uuid=True), nullable=True)
    user_trusts = db.Column(Boolean(), default=True)

    def __init__(self, *args, **kwargs) -> None:
        if args:
            chassis = ComputerChassis(args[0])
            super().__init__(chassis=chassis, **kwargs)
        else:
            super().__init__(*args, **kwargs)

    @property
    def actions(self) -> list:
        actions = copy.copy(super().actions)
        actions_parent = copy.copy(self.actions_parent)
        for ac in actions_parent:
            ac.real_created = ac.created

        return sorted(chain(actions, actions_parent), key=lambda x: x.real_created)
        # return sorted(chain(super().actions, self.actions_parent))

    @property
    def ram_size(self) -> int:
        """The total of RAM memory the computer has."""
        components = self.components
        if self.placeholder and self.placeholder.binding:
            components = self.placeholder.binding.components
        return sum(ram.size or 0 for ram in components if isinstance(ram, RamModule))

    @property
    def data_storage_size(self) -> int:
        """The total of data storage the computer has."""
        components = self.components
        if self.placeholder and self.placeholder.binding:
            components = self.placeholder.binding.components
        return sum(ds.size or 0 for ds in components if isinstance(ds, DataStorage))

    @property
    def processor_model(self) -> str:
        """The model of one of the processors of the computer."""
        return next(
            (p.model for p in self.components if isinstance(p, Processor)), None
        )

    @property
    def graphic_card_model(self) -> str:
        """The model of one of the graphic cards of the computer."""
        return next(
            (p.model for p in self.components if isinstance(p, GraphicCard)), None
        )

    @property
    def network_speeds(self) -> List[int]:
        """Returns two values representing the speeds of the network
        adapters of the device.

        1. The max Ethernet speed of the computer, 0 if ethernet
           adaptor exists but its speed is unknown, None if no eth
           adaptor exists.
        2. The max WiFi speed of the computer, 0 if computer has
           WiFi but its speed is unknown, None if no WiFi adaptor
           exists.
        """
        speeds = [None, None]
        for net in (c for c in self.components if isinstance(c, NetworkAdapter)):
            speeds[net.wireless] = max(net.speed or 0, speeds[net.wireless] or 0)
        return speeds

    @property
    def privacy(self):
        """Returns the privacy of all ``DataStorage`` components when
        it is not None.
        """
        components = self.components
        if self.placeholder and self.placeholder.binding:
            components = self.placeholder.binding.components

        return set(
            privacy
            for privacy in (
                hdd.privacy for hdd in components if isinstance(hdd, DataStorage)
            )
            if privacy
        )

    @property
    def last_erase_action(self):
        components = self.components
        if self.placeholder and self.placeholder.binding:
            components = self.placeholder.binding.components

        return set(
            ac
            for ac in (
                hdd.last_erase_action
                for hdd in components
                if isinstance(hdd, DataStorage)
            )
            if ac
        )

    @property
    def external_document_erasure(self):
        """Returns the external ``DataStorage`` proof of erasure."""
        from ereuse_devicehub.resources.action.models import EraseDataWipe

        urls = set()
        try:
            ev = self.last_action_of(EraseDataWipe)
            urls.add(ev.document.url.to_text())
        except LookupError:
            pass

        for comp in self.components:
            if isinstance(comp, DataStorage):
                doc = comp.external_document_erasure
                if doc:
                    urls.add(doc)
        return urls

    def add_mac_to_hid(self, components_snap=None):
        """Returns the Naming.hid with the first mac of network adapter,
        following an alphabetical order.
        """
        self.set_hid()
        if not self.hid:
            return
        components = self.components if components_snap is None else components_snap
        macs_network = [
            c.serial_number
            for c in components
            if c.type == 'NetworkAdapter' and c.serial_number is not None
        ]
        macs_network.sort()
        mac = macs_network[0] if macs_network else ''
        if not mac or mac in self.hid:
            return
        mac = f"-{mac}"
        self.hid += mac

    def __format__(self, format_spec):
        if not format_spec:
            return super().__format__(format_spec)
        v = ''
        if 't' in format_spec:
            v += '{0.chassis} {0.model}'.format(self)
        elif 's' in format_spec:
            v += '({0.manufacturer})'.format(self)
            if self.serial_number:
                v += ' S/N ' + self.serial_number.upper()
        return v


class Desktop(Computer):
    pass


class Laptop(Computer):
    layout = Column(DBEnum(Layouts))
    layout.comment = """Layout of a built-in keyboard of the computer,
     if any.
     """


class Server(Computer):
    pass


class Monitor(DisplayMixin, Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)


class ComputerMonitor(Monitor):
    pass


class TelevisionSet(Monitor):
    pass


class Projector(Monitor):
    pass


class Mobile(Device):
    """A mobile device consisting of smartphones, tablets, and cellphones."""

    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    imei = Column(BigInteger)
    imei.comment = """The International Mobile Equipment Identity of
    the smartphone as an integer.
    """
    meid = Column(Unicode)
    meid.comment = """The Mobile Equipment Identifier as a hexadecimal
    string.
    """
    ram_size = db.Column(db.Integer, check_range('ram_size', min=128, max=36000))
    ram_size.comment = """The total of RAM of the device in MB."""
    data_storage_size = db.Column(
        db.Integer, check_range('data_storage_size', 0, 10**8)
    )
    data_storage_size.comment = """The total of data storage of the device in MB"""
    display_size = db.Column(
        db.Float(decimal_return_scale=1), check_range('display_size', min=0.1, max=30.0)
    )
    display_size.comment = """The total size of the device screen"""

    # @validates('imei')
    # def validate_imei(self, _, value: int):
    #     if value and not imei.is_valid(str(value)):
    #         raise ValidationError('{} is not a valid imei.'.format(value))
    #     return value

    @validates('meid')
    def validate_meid(self, _, value: str):
        if value and not meid.is_valid(value):
            raise ValidationError('{} is not a valid meid.'.format(value))
        return value

    @property
    def last_erase_action(self):
        erase_auto = None
        erase_manual = None

        if self.binding:
            erase_auto = self.privacy
            erase_manual = self.binding.device.privacy
        if self.placeholder:
            erase_manual = self.privacy
            if self.placeholder.binding:
                erase_auto = self.placeholder.binding.privacy

        if erase_auto and erase_manual:
            return (
                erase_auto
                if erase_auto.created > erase_manual.created
                else erase_manual
            )
        if erase_manual:
            return erase_manual
        if erase_auto:
            return erase_auto
        return None

    @property
    def privacy(self):
        """Returns the privacy compliance state of the data storage.

        This is, the last erasure performed to the data storage.
        """
        from ereuse_devicehub.resources.action.models import EraseBasic

        try:
            ev = self.last_action_of(EraseBasic)
        except LookupError:
            ev = None
        return ev

    def get_size(self):
        return self.data_storage_size


class Smartphone(Mobile):
    pass


class Tablet(Mobile):
    pass


class Cellphone(Mobile):
    pass


class Component(Device):
    """A device that can be inside another device."""

    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)

    parent_id = Column(BigInteger, ForeignKey(Computer.id))
    parent = relationship(
        Computer,
        backref=backref(
            'components',
            lazy=True,
            cascade=CASCADE_DEL,
            order_by=lambda: Component.id,
            collection_class=OrderedSet,
        ),
        primaryjoin=parent_id == Computer.id,
    )

    __table_args__ = (db.Index('parent_index', parent_id, postgresql_using='hash'),)

    def similar_one(self, parent: Computer, blacklist: Set[int]) -> 'Component':
        """Gets a component that:

        * has the same parent.
        * Doesn't generate HID.
        * Has same physical properties.
        :param parent:
        :param blacklist: A set of components to not to consider
                          when looking for similar ones.
        """
        assert self.hid is None, 'Don\'t use this method with a component that has HID'
        component = (
            self.__class__.query.filter_by(
                parent=parent,
                hid=None,
                owner_id=self.owner_id,
                **self.physical_properties,
            )
            .filter(~Component.id.in_(blacklist))
            .first()
        )
        if not component:
            raise ResourceNotFound(self.type)
        return component

    @property
    def actions(self) -> list:
        return sorted(chain(super().actions, self.actions_components))


class JoinedComponentTableMixin:
    @declared_attr
    def id(cls):
        return Column(BigInteger, ForeignKey(Component.id), primary_key=True)


class GraphicCard(JoinedComponentTableMixin, Component):
    memory = Column(SmallInteger, check_range('memory', min=1, max=10000))
    memory.comment = """The amount of memory of the Graphic Card in MB."""


class DataStorage(JoinedComponentTableMixin, Component):
    """A device that stores information."""

    size = Column(Integer, check_range('size', min=1, max=10**8))
    size.comment = """The size of the data-storage in MB."""
    interface = Column(DBEnum(DataStorageInterface))

    @property
    def privacy(self):
        """Returns the privacy compliance state of the data storage.

        This is, the last erasure performed to the data storage.
        """
        from ereuse_devicehub.resources.action.models import EraseBasic

        try:
            ev = self.last_action_of(EraseBasic)
        except LookupError:
            ev = None
        return ev

    @property
    def last_erase_action(self):
        erase_auto = None
        erase_manual = None

        if self.binding:
            erase_auto = self.privacy
            erase_manual = self.binding.device.privacy
        if self.placeholder:
            erase_manual = self.privacy
            if self.placeholder.binding:
                erase_auto = self.placeholder.binding.privacy

        if erase_auto and erase_manual:
            return (
                erase_auto
                if erase_auto.created > erase_manual.created
                else erase_manual
            )
        if erase_manual:
            return erase_manual
        if erase_auto:
            return erase_auto
        return None

    def __format__(self, format_spec):
        v = super().__format__(format_spec)
        if 's' in format_spec:
            v += ' – {} GB'.format(self.size // 1000 if self.size else '?')
        return v

    def get_size(self):
        return '{} GB'.format(self.size // 1000 if self.size else '?')

    @property
    def external_document_erasure(self):
        """Returns the external ``DataStorage`` proof of erasure."""
        from ereuse_devicehub.resources.action.models import DataWipe

        try:
            ev = self.last_action_of(DataWipe)
            return ev.document.url.to_text()
        except LookupError:
            return None

    @property
    def orphan(self):
        if not self.parent:
            return True

        if self.parent.placeholder and self.parent.placeholder.kangaroo:
            return True

        if self.parent.binding and self.parent.binding.kangaroo:
            return True

        return False


class HardDrive(DataStorage):
    pass


class SolidStateDrive(DataStorage):
    pass


class Motherboard(JoinedComponentTableMixin, Component):
    slots = Column(SmallInteger, check_range('slots', min=0))
    slots.comment = """PCI slots the motherboard has."""
    usb = Column(SmallInteger, check_range('usb', min=0))
    firewire = Column(SmallInteger, check_range('firewire', min=0))
    serial = Column(SmallInteger, check_range('serial', min=0))
    pcmcia = Column(SmallInteger, check_range('pcmcia', min=0))
    bios_date = Column(db.Date)
    bios_date.comment = """The date of the BIOS version."""
    ram_slots = Column(db.SmallInteger, check_range('ram_slots'))
    ram_max_size = Column(db.Integer, check_range('ram_max_size'))


class NetworkMixin:
    speed = Column(SmallInteger, check_range('speed', min=10, max=10000))
    speed.comment = """The maximum speed this network adapter can handle,
    in mbps.
    """
    wireless = Column(Boolean, nullable=False, default=False)
    wireless.comment = """Whether it is a wireless interface."""

    def __format__(self, format_spec):
        v = super().__format__(format_spec)
        if 's' in format_spec:
            v += ' – {} Mbps'.format(self.speed)
        return v


class NetworkAdapter(JoinedComponentTableMixin, NetworkMixin, Component):
    pass


class Processor(JoinedComponentTableMixin, Component):
    """The CPU."""

    speed = Column(Float, check_range('speed', 0.1, 15))
    speed.comment = """The regular CPU speed."""
    cores = Column(SmallInteger, check_range('cores', 1, 10))
    cores.comment = """The number of regular cores."""
    threads = Column(SmallInteger, check_range('threads', 1, 20))
    threads.comment = """The number of threads per core."""
    address = Column(SmallInteger, check_range('address', 8, 256))
    address.comment = """The address of the CPU: 8, 16, 32, 64, 128 or 256 bits."""
    abi = Column(Unicode, check_lower('abi'))
    abi.comment = """The Application Binary Interface of the processor."""


class RamModule(JoinedComponentTableMixin, Component):
    """A stick of RAM."""

    size = Column(SmallInteger, check_range('size', min=128, max=17000))
    size.comment = """The capacity of the RAM stick."""
    speed = Column(SmallInteger, check_range('speed', min=100, max=10000))
    interface = Column(DBEnum(RamInterface))
    format = Column(DBEnum(RamFormat))


class SoundCard(JoinedComponentTableMixin, Component):
    pass


class Display(JoinedComponentTableMixin, DisplayMixin, Component):
    """The display of a device. This is used in all devices that have
    displays but that it is not their main part, like laptops,
    mobiles, smart-watches, and so on; excluding ``ComputerMonitor``
    and ``TelevisionSet``.
    """

    pass


class Battery(JoinedComponentTableMixin, Component):
    wireless = db.Column(db.Boolean)
    wireless.comment = """If the battery can be charged wirelessly."""
    technology = db.Column(db.Enum(BatteryTechnology))
    size = db.Column(db.Integer, nullable=False)
    size.comment = """Maximum battery capacity by design, in mAh.

    Use BatteryTest's "size" to get the actual size of the battery.
    """

    @property
    def capacity(self) -> float:
        """The quantity of"""
        from ereuse_devicehub.resources.action.models import MeasureBattery

        real_size = self.last_action_of(MeasureBattery).size
        return real_size / self.size if real_size and self.size else None


class Camera(Component):
    """The camera of a device."""

    focal_length = db.Column(db.SmallInteger)
    video_height = db.Column(db.SmallInteger)
    video_width = db.Column(db.Integer)
    horizontal_view_angle = db.Column(db.Integer)
    facing = db.Column(db.Enum(CameraFacing))
    vertical_view_angle = db.Column(db.SmallInteger)
    video_stabilization = db.Column(db.Boolean)
    flash = db.Column(db.Boolean)


class ComputerAccessory(Device):
    """Computer peripherals and similar accessories."""

    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    pass


class SAI(ComputerAccessory):
    pass


class Keyboard(ComputerAccessory):
    layout = Column(DBEnum(Layouts))  # If we want to do it not null


class Mouse(ComputerAccessory):
    pass


class MemoryCardReader(ComputerAccessory):
    pass


class Networking(NetworkMixin, Device):
    """Routers, switches, hubs..."""

    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)


class Router(Networking):
    pass


class Switch(Networking):
    pass


class Hub(Networking):
    pass


class WirelessAccessPoint(Networking):
    pass


class Printer(Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
    wireless = Column(Boolean, nullable=False, default=False)
    wireless.comment = """Whether it is a wireless printer."""
    scanning = Column(Boolean, nullable=False, default=False)
    scanning.comment = """Whether the printer has scanning capabilities."""
    technology = Column(DBEnum(PrinterTechnology))
    technology.comment = """Technology used to print."""
    monochrome = Column(Boolean, nullable=False, default=True)
    monochrome.comment = """Whether the printer is only monochrome."""


class LabelPrinter(Printer):
    pass


class Sound(Device):
    pass


class Microphone(Sound):
    pass


class Video(Device):
    """Devices related to video treatment."""

    pass


class VideoScaler(Video):
    pass


class Videoconference(Video):
    pass


class Cooking(Device):
    """Cooking devices."""

    pass


class Mixer(Cooking):
    pass


class DIYAndGardening(Device):
    pass


class Drill(DIYAndGardening):
    max_drill_bit_size = db.Column(db.SmallInteger)


class PackOfScrewdrivers(Device):
    pass


class Home(Device):
    pass


class Dehumidifier(Home):
    size = db.Column(db.SmallInteger)
    size.comment = """The capacity in Liters."""


class Stairs(Home):
    max_allowed_weight = db.Column(db.Integer)


class Recreation(Device):
    pass


class Bike(Recreation):
    wheel_size = db.Column(db.SmallInteger)
    gears = db.Column(db.SmallInteger)


class Racket(Recreation):
    pass


class Manufacturer(db.Model):
    """The normalized information about a manufacturer.

    Ideally users should use the names from this list when submitting
    devices.
    """

    name = db.Column(CIText(), primary_key=True)
    name.comment = """The normalized name of the manufacturer."""
    url = db.Column(URL(), unique=True)
    url.comment = """An URL to a page describing the manufacturer."""
    logo = db.Column(URL())
    logo.comment = """An URL pointing to the logo of the manufacturer."""

    __table_args__ = (
        # from https://niallburkley.com/blog/index-columns-for-like-in-postgres/
        db.Index('name_index', text('name gin_trgm_ops'), postgresql_using='gin'),
        {'schema': 'common'},
    )

    @classmethod
    def add_all_to_session(cls, session: db.Session):
        """Adds all manufacturers to session."""
        cursor = session.connection().connection.cursor()
        #: Dialect used to write the CSV

        with pathlib.Path(__file__).parent.joinpath('manufacturers.csv').open() as f:
            cursor.copy_expert('COPY common.manufacturer FROM STDIN (FORMAT csv)', f)


listener_reset_field_updated_in_actual_time(Device)


def create_code_tag(mapper, connection, device):
    """
    This function create a new tag every time than one device is create.
    this tag is the same of devicehub_id.
    """
    from ereuse_devicehub.resources.tag.model import Tag

    if isinstance(device, Computer) and not device.placeholder:
        tag = Tag(device_id=device.id, id=device.devicehub_id)
        db.session.add(tag)


# from flask_sqlalchemy import event
# event.listen(Device, 'after_insert', create_code_tag, propagate=True)


class Other(Device):
    """
    Used for put in there all devices than not have actualy a class
    """

    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)
