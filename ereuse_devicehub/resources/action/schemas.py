import copy
from datetime import datetime, timedelta

from dateutil.tz import tzutc
from flask import current_app as app
from flask import g
from marshmallow import Schema as MarshmallowSchema
from marshmallow import ValidationError
from marshmallow import fields as f
from marshmallow import post_load, pre_load, validates_schema
from marshmallow.fields import (
    UUID,
    Boolean,
    DateTime,
    Decimal,
    Float,
    Integer,
    Nested,
    String,
    TimeDelta,
)
from marshmallow.validate import Length, OneOf, Range
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources import enums
from ereuse_devicehub.resources.action import models as m
from ereuse_devicehub.resources.agent import schemas as s_agent
from ereuse_devicehub.resources.device import schemas as s_device
from ereuse_devicehub.resources.documents import schemas as s_generic_document
from ereuse_devicehub.resources.enums import (
    R_POSITIVE,
    AppearanceRange,
    BiosAccessRange,
    FunctionalityRange,
    PhysicalErasureMethod,
    RatingRange,
    Severity,
    SnapshotSoftware,
    TestDataStorageLength,
)
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.tradedocument import schemas as s_document
from ereuse_devicehub.resources.tradedocument.models import TradeDocument
from ereuse_devicehub.resources.user import schemas as s_user
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.teal.enums import Currency
from ereuse_devicehub.teal.marshmallow import URL, EnumField, SanitizedStr, Version
from ereuse_devicehub.teal.resource import Schema


class Action(Thing):
    __doc__ = m.Action.__doc__
    id = UUID(dump_only=True)
    name = SanitizedStr(
        default='', validate=Length(max=STR_BIG_SIZE), description=m.Action.name.comment
    )
    closed = Boolean(missing=True, description=m.Action.closed.comment)
    severity = EnumField(Severity, description=m.Action.severity.comment)
    description = SanitizedStr(default='', description=m.Action.description.comment)
    start_time = DateTime(data_key='startTime', description=m.Action.start_time.comment)
    end_time = DateTime(data_key='endTime', description=m.Action.end_time.comment)
    snapshot = NestedOn('Snapshot', dump_only=True)
    agent = NestedOn(s_agent.Agent, description=m.Action.agent_id.comment)
    author = NestedOn(s_user.User, dump_only=True, exclude=('token',))
    components = NestedOn(s_device.Component, dump_only=True, many=True)
    parent = NestedOn(
        s_device.Computer, dump_only=True, description=m.Action.parent_id.comment
    )
    url = URL(dump_only=True, description=m.Action.url.__doc__)

    @validates_schema
    def validate_times(self, data: dict):
        unix_time = datetime.fromisoformat("1970-01-02 00:00:00+00:00")
        if 'end_time' in data and data['end_time'].replace(tzinfo=tzutc()) < unix_time:
            data['end_time'] = unix_time

        if (
            'start_time' in data
            and data['start_time'].replace(tzinfo=tzutc()) < unix_time
        ):
            data['start_time'] = unix_time

        if data.get('end_time') and data.get('start_time'):
            if data['start_time'] > data['end_time']:
                raise ValidationError('The action cannot finish before it starts.')


class ActionWithOneDevice(Action):
    __doc__ = m.ActionWithOneDevice.__doc__
    device = NestedOn(s_device.Device, only_query='id')


class ActionWithMultipleDocuments(Action):
    __doc__ = m.ActionWithMultipleTradeDocuments.__doc__
    documents = NestedOn(
        s_document.TradeDocument,
        many=True,
        required=True,  # todo test ensuring len(devices) >= 1
        only_query='id',
        collection_class=OrderedSet,
    )


class ActionWithMultipleDevices(Action):
    __doc__ = m.ActionWithMultipleDevices.__doc__
    devices = NestedOn(
        s_device.Device,
        many=True,
        required=True,  # todo test ensuring len(devices) >= 1
        only_query='id',
        collection_class=OrderedSet,
    )


class ActionWithMultipleDevicesCheckingOwner(ActionWithMultipleDevices):
    @post_load
    def check_owner_of_device(self, data):
        for dev in data['devices']:
            if dev.owner != g.user:
                raise ValidationError("Some Devices not exist")


class Add(ActionWithOneDevice):
    __doc__ = m.Add.__doc__


class Remove(ActionWithOneDevice):
    __doc__ = m.Remove.__doc__


class Allocate(ActionWithMultipleDevicesCheckingOwner):
    __doc__ = m.Allocate.__doc__
    start_time = DateTime(
        data_key='startTime', required=True, description=m.Action.start_time.comment
    )
    end_time = DateTime(
        data_key='endTime', required=False, description=m.Action.end_time.comment
    )
    final_user_code = SanitizedStr(
        data_key="finalUserCode",
        validate=Length(min=1, max=STR_BIG_SIZE),
        required=False,
        description='This is a internal code for mainteing the secrets of the \
                                               personal datas of the new holder',
    )
    transaction = SanitizedStr(
        validate=Length(min=1, max=STR_BIG_SIZE),
        required=False,
        description='The code used from the owner for \
                                relation with external tool.',
    )
    end_users = Integer(
        data_key='endUsers',
        validate=[Range(min=1, error="Value must be greater than 0")],
    )

    @validates_schema
    def validate_allocate(self, data: dict):
        txt = "You need to allocate for a day before today"
        delay = timedelta(days=1)
        today = datetime.now().replace(tzinfo=tzutc()) + delay
        start_time = data['start_time'].replace(tzinfo=tzutc())
        if start_time > today:
            raise ValidationError(txt)

        txt = "You need deallocate before allocate this device again"
        for device in data['devices']:
            if device.allocated:
                raise ValidationError(txt)

            device.allocated = True


class Deallocate(ActionWithMultipleDevicesCheckingOwner):
    __doc__ = m.Deallocate.__doc__
    start_time = DateTime(
        data_key='startTime', required=True, description=m.Action.start_time.comment
    )
    transaction = SanitizedStr(
        validate=Length(min=1, max=STR_BIG_SIZE),
        required=False,
        description='The code used from the owner for \
                                relation with external tool.',
    )

    @validates_schema
    def validate_deallocate(self, data: dict):
        txt = "You need to deallocate for a day before today"
        delay = timedelta(days=1)
        today = datetime.now().replace(tzinfo=tzutc()) + delay
        start_time = data['start_time'].replace(tzinfo=tzutc())
        if start_time > today:
            raise ValidationError(txt)

        txt = "Sorry some of this devices are actually deallocate"
        for device in data['devices']:
            if not device.allocated:
                raise ValidationError(txt)

            device.allocated = False


class EraseBasic(ActionWithOneDevice):
    __doc__ = m.EraseBasic.__doc__
    steps = NestedOn('Step', many=True)
    standards = f.List(EnumField(enums.ErasureStandards), dump_only=True)
    certificate = URL(dump_only=True)


class EraseSectors(EraseBasic):
    __doc__ = m.EraseSectors.__doc__


class ErasePhysical(EraseBasic):
    __doc__ = m.ErasePhysical.__doc__
    method = EnumField(PhysicalErasureMethod, description=PhysicalErasureMethod.__doc__)


class Step(Schema):
    __doc__ = m.Step.__doc__
    type = String(description='Only required when it is nested.')
    start_time = DateTime(required=True, data_key='startTime')
    end_time = DateTime(required=True, data_key='endTime')
    severity = EnumField(Severity, description=m.Action.severity.comment)


class StepZero(Step):
    __doc__ = m.StepZero.__doc__


class StepRandom(Step):
    __doc__ = m.StepRandom.__doc__


class Benchmark(ActionWithOneDevice):
    __doc__ = m.Benchmark.__doc__
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)


class BenchmarkDataStorage(Benchmark):
    __doc__ = m.BenchmarkDataStorage.__doc__
    read_speed = Float(required=True, data_key='readSpeed')
    write_speed = Float(required=True, data_key='writeSpeed')


class BenchmarkWithRate(Benchmark):
    __doc__ = m.BenchmarkWithRate.__doc__
    rate = Float(required=True)


class BenchmarkProcessor(BenchmarkWithRate):
    __doc__ = m.BenchmarkProcessor.__doc__


class BenchmarkProcessorSysbench(BenchmarkProcessor):
    __doc__ = m.BenchmarkProcessorSysbench.__doc__


class BenchmarkRamSysbench(BenchmarkWithRate):
    __doc__ = m.BenchmarkRamSysbench.__doc__


class BenchmarkGraphicCard(BenchmarkWithRate):
    __doc__ = m.BenchmarkGraphicCard.__doc__


class Test(ActionWithOneDevice):
    __doc__ = m.Test.__doc__


class MeasureBattery(Test):
    __doc__ = m.MeasureBattery.__doc__
    size = Integer(required=True, description=m.MeasureBattery.size.comment)
    voltage = Integer(required=True, description=m.MeasureBattery.voltage.comment)
    cycle_count = Integer(
        data_key='cycleCount', description=m.MeasureBattery.cycle_count.comment
    )
    health = EnumField(enums.BatteryHealth, description=m.MeasureBattery.health.comment)


class TestDataStorage(Test):
    __doc__ = m.TestDataStorage.__doc__
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)
    length = EnumField(TestDataStorageLength, required=True)
    status = SanitizedStr(lower=True, validate=Length(max=STR_SIZE), required=True)
    lifetime = TimeDelta(precision=TimeDelta.HOURS)
    power_on_hours = Integer(data_key='powerOnHours', dump_only=True)
    assessment = Boolean()
    reallocated_sector_count = Integer(data_key='reallocatedSectorCount')
    power_cycle_count = Integer(data_key='powerCycleCount')
    reported_uncorrectable_errors = Integer(data_key='reportedUncorrectableErrors')
    command_timeout = Integer(data_key='commandTimeout')
    current_pending_sector_count = Integer(data_key='currentPendingSectorCount')
    offline_uncorrectable = Integer(data_key='offlineUncorrectable')
    remaining_lifetime_percentage = Integer(data_key='remainingLifetimePercentage')

    @post_load
    def default_remaining_lifetime_percentage(self, data):
        if not data.get('remaining_lifetime_percentage'):
            return

        if data.get('remaining_lifetime_percentage') > 100:
            data['remaining_lifetime_percentage'] = None


class StressTest(Test):
    __doc__ = m.StressTest.__doc__
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)


class TestAudio(Test):
    __doc__ = m.TestAudio.__doc__
    speaker = Boolean(description=m.TestAudio._speaker.comment)
    microphone = Boolean(description=m.TestAudio._microphone.comment)


class TestConnectivity(Test):
    __doc__ = m.TestConnectivity.__doc__


class TestCamera(Test):
    __doc__ = m.TestCamera.__doc__


class TestKeyboard(Test):
    __doc__ = m.TestKeyboard.__doc__


class TestTrackpad(Test):
    __doc__ = m.TestTrackpad.__doc__


class TestBios(Test):
    __doc__ = m.TestBios.__doc__
    bios_power_on = Boolean()
    access_range = EnumField(BiosAccessRange, data_key='accessRange')


class VisualTest(Test):
    __doc__ = m.VisualTest.__doc__
    appearance_range = EnumField(AppearanceRange, data_key='appearanceRange')
    functionality_range = EnumField(FunctionalityRange, data_key='functionalityRange')
    labelling = Boolean()


class Rate(ActionWithOneDevice):
    __doc__ = m.Rate.__doc__
    rating = Integer(
        validate=Range(*R_POSITIVE), dump_only=True, description=m.Rate._rating.comment
    )
    version = Version(dump_only=True, description=m.Rate.version.comment)
    appearance = Integer(
        validate=Range(enums.R_NEGATIVE),
        dump_only=True,
        description=m.Rate._appearance.comment,
    )
    functionality = Integer(
        validate=Range(enums.R_NEGATIVE),
        dump_only=True,
        description=m.Rate._functionality.comment,
    )
    rating_range = EnumField(
        RatingRange,
        dump_only=True,
        data_key='ratingRange',
        description=m.Rate.rating_range.__doc__,
    )


class RateComputer(Rate):
    __doc__ = m.RateComputer.__doc__
    processor = Float(dump_only=True)
    ram = Float(dump_only=True)
    data_storage = Float(dump_only=True, data_key='dataStorage')
    graphic_card = Float(dump_only=True, data_key='graphicCard')

    data_storage_range = EnumField(
        RatingRange, dump_only=True, data_key='dataStorageRange'
    )
    ram_range = EnumField(RatingRange, dump_only=True, data_key='ramRange')
    processor_range = EnumField(RatingRange, dump_only=True, data_key='processorRange')
    graphic_card_range = EnumField(
        RatingRange, dump_only=True, data_key='graphicCardRange'
    )


class Price(ActionWithOneDevice):
    __doc__ = m.Price.__doc__
    currency = EnumField(Currency, required=True, description=m.Price.currency.comment)
    price = Decimal(
        places=m.Price.SCALE,
        rounding=m.Price.ROUND,
        required=True,
        description=m.Price.price.comment,
    )
    version = Version(dump_only=True, description=m.Price.version.comment)
    rating = NestedOn(Rate, dump_only=True, description=m.Price.rating_id.comment)


class EreusePrice(Price):
    __doc__ = m.EreusePrice.__doc__

    class Service(MarshmallowSchema):
        class Type(MarshmallowSchema):
            amount = Float()
            percentage = Float()

        standard = Nested(Type)
        warranty2 = Nested(Type)

    warranty2 = Float()
    refurbisher = Nested(Service)
    retailer = Nested(Service)
    platform = Nested(Service)


class Install(ActionWithOneDevice):
    __doc__ = m.Install.__doc__
    name = SanitizedStr(
        validate=Length(min=4, max=STR_BIG_SIZE),
        required=True,
        description='The name of the OS installed.',
    )
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)
    address = Integer(validate=OneOf({8, 16, 32, 64, 128, 256}))


class Snapshot(ActionWithOneDevice):
    __doc__ = m.Snapshot.__doc__
    """
    The Snapshot updates the state of the device with information about
    its components and actions performed at them.

    See docs for more info.
    """
    uuid = UUID()
    sid = String(required=False)
    software = EnumField(
        SnapshotSoftware,
        required=True,
        description='The software that generated this Snapshot.',
    )
    version = Version(required=True, description='The version of the software.')
    actions = NestedOn(Action, many=True, dump_only=True)
    elapsed = TimeDelta(precision=TimeDelta.SECONDS)
    components = NestedOn(
        s_device.Component,
        many=True,
        description='A list of components that are inside of the device'
        'at the moment of this Snapshot.'
        'Order is preserved, so the component num 0 when'
        'submitting is the component num 0 when returning it back.',
    )
    settings_version = String(required=False)

    @validates_schema
    def validate_workbench_version(self, data: dict):
        if data['software'] == SnapshotSoftware.Workbench:
            if data['version'] < app.config['MIN_WORKBENCH']:
                raise ValidationError(
                    'Min. supported Workbench version is '
                    '{} but yours is {}.'.format(
                        app.config['MIN_WORKBENCH'], data['version']
                    ),
                    field_names=['version'],
                )

    @validates_schema
    def validate_components_only_workbench(self, data: dict):
        if (data['software'] != SnapshotSoftware.Workbench) and (
            data['software'] != SnapshotSoftware.WorkbenchAndroid
        ):
            if data.get('components', None) is not None:
                raise ValidationError(
                    'Only Workbench can add component info', field_names=['components']
                )

    @validates_schema
    def validate_only_workbench_fields(self, data: dict):
        """Ensures workbench has ``elapsed`` and ``uuid`` and no others."""
        # todo test
        if data['software'] == SnapshotSoftware.Workbench:
            if not data.get('uuid', None):
                raise ValidationError(
                    'Snapshots from Workbench and WorkbenchAndroid must have uuid',
                    field_names=['uuid'],
                )
            if data.get('elapsed', None) is None:
                raise ValidationError(
                    'Snapshots from Workbench must have elapsed',
                    field_names=['elapsed'],
                )
        elif data['software'] == SnapshotSoftware.WorkbenchAndroid:
            if not data.get('uuid', None):
                raise ValidationError(
                    'Snapshots from Workbench and WorkbenchAndroid must have uuid',
                    field_names=['uuid'],
                )
        else:
            if data.get('uuid', None):
                raise ValidationError(
                    'Only Snapshots from Workbench or WorkbenchAndroid can have uuid',
                    field_names=['uuid'],
                )
            if data.get('elapsed', None):
                raise ValidationError(
                    'Only Snapshots from Workbench can have elapsed',
                    field_names=['elapsed'],
                )


class ToRepair(ActionWithMultipleDevicesCheckingOwner):
    __doc__ = m.ToRepair.__doc__


class Repair(ActionWithMultipleDevicesCheckingOwner):
    __doc__ = m.Repair.__doc__


class Ready(ActionWithMultipleDevicesCheckingOwner):
    __doc__ = m.Ready.__doc__


class EWaste(ActionWithMultipleDevicesCheckingOwner):
    __doc__ = m.EWaste.__doc__


class ActionStatus(Action):
    rol_user = NestedOn(s_user.User, dump_only=True, exclude=('token',))
    devices = NestedOn(
        s_device.Device,
        many=True,
        required=False,  # todo test ensuring len(devices) >= 1
        only_query='id',
        collection_class=OrderedSet,
    )
    documents = NestedOn(
        s_document.TradeDocument,
        many=True,
        required=False,  # todo test ensuring len(devices) >= 1
        only_query='id',
        collection_class=OrderedSet,
    )

    @pre_load
    def put_devices(self, data: dict):
        if 'devices' not in data.keys():
            data['devices'] = []

    @post_load
    def put_rol_user(self, data: dict):
        for dev in data['devices']:
            trades = [ac for ac in dev.actions if ac.t == 'Trade']
            if not trades:
                return data

            trade = trades[-1]

            if trade.user_from == g.user:
                data['rol_user'] = trade.user_to
            data['trade'] = trade


class Recycling(ActionStatus):
    __doc__ = m.Recycling.__doc__


class Use(ActionStatus):
    __doc__ = m.Use.__doc__


class Refurbish(ActionStatus):
    __doc__ = m.Refurbish.__doc__


class Management(ActionStatus):
    __doc__ = m.Management.__doc__


class ToPrepare(ActionWithMultipleDevicesCheckingOwner):
    __doc__ = m.ToPrepare.__doc__


class Prepare(ActionWithMultipleDevicesCheckingOwner):
    __doc__ = m.Prepare.__doc__


class DataWipe(ActionWithMultipleDevicesCheckingOwner):
    __doc__ = m.DataWipe.__doc__
    document = NestedOn(s_generic_document.DataWipeDocument, only_query='id')


class EraseDataWipe(ActionWithMultipleDevicesCheckingOwner):
    __doc__ = m.DataWipe.__doc__
    document = NestedOn(s_generic_document.DataWipeDocument, only_query='id')


class Live(ActionWithOneDevice):
    __doc__ = m.Live.__doc__
    """
    The Snapshot updates the state of the device with information about
    its components and actions performed at them.

    See docs for more info.
    """
    uuid = UUID()
    software = EnumField(
        SnapshotSoftware,
        required=True,
        description='The software that generated this Snapshot.',
    )
    version = Version(required=True, description='The version of the software.')
    final_user_code = SanitizedStr(data_key="finalUserCode", dump_only=True)
    licence_version = Version(required=True, description='The version of the software.')
    components = NestedOn(
        s_device.Component,
        many=True,
        description='A list of components that are inside of the device'
        'at the moment of this Snapshot.'
        'Order is preserved, so the component num 0 when'
        'submitting is the component num 0 when returning it back.',
    )
    usage_time_allocate = TimeDelta(
        data_key='usageTimeAllocate',
        required=False,
        precision=TimeDelta.HOURS,
        dump_only=True,
    )


class Organize(ActionWithMultipleDevices):
    __doc__ = m.Organize.__doc__


class Reserve(Organize):
    __doc__ = m.Reserve.__doc__


class CancelReservation(Organize):
    __doc__ = m.CancelReservation.__doc__


class Confirm(ActionWithMultipleDevices):
    __doc__ = m.Confirm.__doc__
    action = NestedOn('Action', only_query='id')

    @validates_schema
    def validate_revoke(self, data: dict):
        for dev in data['devices']:
            # if device not exist in the Trade, then this query is wrong
            if dev not in data['action'].devices:
                txt = "Device {} not exist in the trade".format(dev.devicehub_id)
                raise ValidationError(txt)


class Revoke(ActionWithMultipleDevices):
    __doc__ = m.Revoke.__doc__
    action = NestedOn('Action', only_query='id')

    @validates_schema
    def validate_revoke(self, data: dict):
        for dev in data['devices']:
            # if device not exist in the Trade, then this query is wrong
            if dev not in data['action'].devices:
                txt = "Device {} not exist in the trade".format(dev.devicehub_id)
                raise ValidationError(txt)

        for doc in data.get('documents', []):
            # if document not exist in the Trade, then this query is wrong
            if doc not in data['action'].documents:
                txt = "Document {} not exist in the trade".format(doc.file_name)
                raise ValidationError(txt)

    @validates_schema
    def validate_documents(self, data):
        """Check if there are or no one before confirmation,
        This is not checked in the view becouse the list of documents is inmutable

        """
        if not data['devices'] == OrderedSet():
            return

        documents = []
        for doc in data['documents']:
            actions = copy.copy(doc.actions)
            actions.reverse()
            for ac in actions:
                if ac == data['action']:
                    # data['action'] is a Trade action, if this is the first action
                    # to find mean that this document don't have a confirmation
                    break

                if ac.t == 'Revoke' and ac.user == g.user:
                    # this doc is confirmation jet
                    break

                if ac.t == Confirm.t and ac.user == g.user:
                    documents.append(doc)
                    break

        if not documents:
            txt = 'No there are documents to revoke'
            raise ValidationError(txt)


class ConfirmRevoke(Revoke):
    pass


class ConfirmDocument(ActionWithMultipleDocuments):
    __doc__ = m.Confirm.__doc__
    action = NestedOn('Action', only_query='id')

    @validates_schema
    def validate_documents(self, data):
        """If there are one device than have one confirmation,
        then remove the list this device of the list of devices of this action
        """
        if data['documents'] == OrderedSet():
            return

        for doc in data['documents']:
            if not doc.lot.trade:
                return

            data['action'] = doc.lot.trade

            if not doc.actions:
                continue

            if not doc.trading == 'Need Confirmation':
                txt = 'No there are documents to confirm'
                raise ValidationError(txt)


class RevokeDocument(ActionWithMultipleDocuments):
    __doc__ = m.RevokeDocument.__doc__
    action = NestedOn('Action', only_query='id')

    @validates_schema
    def validate_documents(self, data):
        """Check if there are or no one before confirmation,
        This is not checked in the view becouse the list of documents is inmutable

        """
        if data['documents'] == OrderedSet():
            return

        for doc in data['documents']:
            if not doc.lot.trade:
                return

            data['action'] = doc.lot.trade

            if not doc.actions:
                continue

            if doc.trading not in ['Document Confirmed', 'Confirm']:
                txt = 'No there are documents to revoke'
                raise ValidationError(txt)


class ConfirmRevokeDocument(ActionWithMultipleDocuments):
    __doc__ = m.ConfirmRevokeDocument.__doc__
    action = NestedOn('Action', only_query='id')

    @validates_schema
    def validate_documents(self, data):
        """Check if there are or no one before confirmation,
        This is not checked in the view becouse the list of documents is inmutable

        """
        if data['documents'] == OrderedSet():
            return

        for doc in data['documents']:
            if not doc.lot.trade:
                return

            if not doc.actions:
                continue

            if not doc.trading == 'Revoke':
                txt = 'No there are documents with revoke for confirm'
                raise ValidationError(txt)

            data['action'] = doc.actions[-1]


class Trade(ActionWithMultipleDevices):
    __doc__ = m.Trade.__doc__
    date = DateTime(data_key='date', required=False)
    price = Float(required=False, data_key='price')
    user_to_email = SanitizedStr(
        validate=Length(max=STR_SIZE),
        data_key='userToEmail',
        missing='',
        required=False,
    )
    user_to = NestedOn(s_user.User, dump_only=True, data_key='userTo')
    user_from_email = SanitizedStr(
        validate=Length(max=STR_SIZE),
        data_key='userFromEmail',
        missing='',
        required=False,
    )
    user_from = NestedOn(s_user.User, dump_only=True, data_key='userFrom')
    code = SanitizedStr(validate=Length(max=STR_SIZE), data_key='code', required=False)
    confirm = Boolean(
        data_key='confirms',
        missing=True,
        description="""If you need confirmation of the user you need actevate this field""",
    )
    lot = NestedOn('Lot', many=False, required=True, only_query='id')

    @pre_load
    def adding_devices(self, data: dict):
        if 'devices' not in data.keys():
            data['devices'] = []

    @validates_schema
    def validate_lot(self, data: dict):
        if g.user.email not in [data['user_from_email'], data['user_to_email']]:
            txt = "you need to be one of the users of involved in the Trade"
            raise ValidationError(txt)

        for dev in data['lot'].devices:
            if not dev.owner == g.user:
                txt = "you need to be the owner of the devices for to do a trade"
                raise ValidationError(txt)

        if not data['lot'].owner == g.user:
            txt = "you need to be the owner of the lot for to do a trade"
            raise ValidationError(txt)

        for doc in data['lot'].documents:
            if not doc.owner == g.user:
                txt = "you need to be the owner of the documents for to do a trade"
                raise ValidationError(txt)

        data['devices'] = data['lot'].devices
        data['documents'] = data['lot'].documents

    @validates_schema
    def validate_user_to_email(self, data: dict):
        """
        - if user_to exist
            * confirmation
            * without confirmation
        - if user_to don't exist
            * without confirmation

        """
        if data['user_to_email']:
            user_to = User.query.filter_by(email=data['user_to_email']).one()
            data['user_to'] = user_to
        else:
            data['confirm'] = False

    @validates_schema
    def validate_user_from_email(self, data: dict):
        """
        - if user_from exist
            * confirmation
            * without confirmation
        - if user_from don't exist
            * without confirmation

        """
        if data['user_from_email']:
            user_from = User.query.filter_by(email=data['user_from_email']).one()
            data['user_from'] = user_from

    @validates_schema
    def validate_email_users(self, data: dict):
        """We need at least one user"""
        confirm = data['confirm']
        user_from = data['user_from_email']
        user_to = data['user_to_email']

        if not (user_from or user_to):
            txt = "you need one user from or user to for to do a trade"
            raise ValidationError(txt)

        if confirm and not (user_from and user_to):
            txt = "you need one user for to do a trade"
            raise ValidationError(txt)

        if g.user.email not in [user_from, user_to]:
            txt = "you need to be one of participate of the action"
            raise ValidationError(txt)

    @validates_schema
    def validate_code(self, data: dict):
        """If the user not exist, you need a code to be able to do the traceability"""
        if data['user_from_email'] and data['user_to_email']:
            data['confirm'] = True
            return

        if not data['confirm'] and not data.get('code'):
            txt = "you need a code to be able to do the traceability"
            raise ValidationError(txt)

        if not data['confirm']:
            data['code'] = data['code'].replace('@', '_')


class InitTransfer(Trade):
    __doc__ = m.InitTransfer.__doc__


class Sell(Trade):
    __doc__ = m.Sell.__doc__


class Donate(Trade):
    __doc__ = m.Donate.__doc__


class Rent(Trade):
    __doc__ = m.Rent.__doc__


class MakeAvailable(ActionWithMultipleDevices):
    __doc__ = m.MakeAvailable.__doc__


class CancelTrade(Trade):
    __doc__ = m.CancelTrade.__doc__


class ToDisposeProduct(Trade):
    __doc__ = m.ToDisposeProduct.__doc__


class DisposeProduct(Trade):
    __doc__ = m.DisposeProduct.__doc__


class TransferOwnershipBlockchain(Trade):
    __doc__ = m.TransferOwnershipBlockchain.__doc__


class Delete(ActionWithMultipleDevicesCheckingOwner):
    __doc__ = m.Delete.__doc__

    @post_load
    def deactivate_device(self, data):
        for dev in data['devices']:
            if dev.last_action_trading is None:
                dev.active = False
                if dev.binding:
                    dev.binding.device.active = False
                if dev.placeholder:
                    dev.placeholder.device.active = False


class Migrate(ActionWithMultipleDevices):
    __doc__ = m.Migrate.__doc__
    other = URL()


class MigrateTo(Migrate):
    __doc__ = m.MigrateTo.__doc__


class MigrateFrom(Migrate):
    __doc__ = m.MigrateFrom.__doc__


class MoveOnDocument(Action):
    __doc__ = m.MoveOnDocument.__doc__
    weight = Integer()
    container_from = NestedOn('TradeDocument', only_query='id')
    container_to = NestedOn('TradeDocument', only_query='id')

    @pre_load
    def extract_container(self, data):
        id_hash = data['container_to']
        docs = TradeDocument.query.filter_by(owner=g.user, file_hash=id_hash).all()
        if len(docs) > 1:
            txt = 'This document it is associated in more than one lot'
            raise ValidationError(txt)

        if len(docs) < 1:
            txt = 'This document not exist'
            raise ValidationError(txt)
        data['container_to'] = docs[0].id

    @post_load
    def adding_documents(self, data):
        """Adding action in the 2 TradeDocuments"""
        docs = OrderedSet()
        docs.add(data['container_to'])
        docs.add(data['container_from'])
        data['documents'] = docs
