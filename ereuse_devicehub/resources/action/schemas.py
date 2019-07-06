from flask import current_app as app
from marshmallow import Schema as MarshmallowSchema, ValidationError, fields as f, validates_schema
from marshmallow.fields import Boolean, DateTime, Decimal, Float, Integer, Nested, String, \
    TimeDelta, UUID
from marshmallow.validate import Length, OneOf, Range
from sqlalchemy.util import OrderedSet
from teal.enums import Country, Currency, Subdivision
from teal.marshmallow import EnumField, IP, SanitizedStr, URL, Version
from teal.resource import Schema

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources import enums
from ereuse_devicehub.resources.action import models as m
from ereuse_devicehub.resources.agent import schemas as s_agent
from ereuse_devicehub.resources.device import schemas as s_device
from ereuse_devicehub.resources.enums import AppearanceRange, BiosAccessRange, FunctionalityRange, \
    PhysicalErasureMethod, R_POSITIVE, RatingRange, ReceiverRole, \
    Severity, SnapshotSoftware, TestDataStorageLength
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.user import schemas as s_user


class Action(Thing):
    __doc__ = m.Action.__doc__
    id = UUID(dump_only=True)
    name = SanitizedStr(default='',
                        validate=Length(max=STR_BIG_SIZE),
                        description=m.Action.name.comment)
    closed = Boolean(missing=True, description=m.Action.closed.comment)
    severity = EnumField(Severity, description=m.Action.severity.comment)
    description = SanitizedStr(default='', description=m.Action.description.comment)
    start_time = DateTime(data_key='startTime', description=m.Action.start_time.comment)
    end_time = DateTime(data_key='endTime', description=m.Action.end_time.comment)
    snapshot = NestedOn('Snapshot', dump_only=True)
    agent = NestedOn(s_agent.Agent, description=m.Action.agent_id.comment)
    author = NestedOn(s_user.User, dump_only=True, exclude=('token',))
    components = NestedOn(s_device.Component, dump_only=True, many=True)
    parent = NestedOn(s_device.Computer, dump_only=True, description=m.Action.parent_id.comment)
    url = URL(dump_only=True, description=m.Action.url.__doc__)


class ActionWithOneDevice(Action):
    __doc__ = m.ActionWithOneDevice.__doc__
    device = NestedOn(s_device.Device, only_query='id')


class ActionWithMultipleDevices(Action):
    __doc__ = m.ActionWithMultipleDevices.__doc__
    devices = NestedOn(s_device.Device, many=True, only_query='id', collection_class=OrderedSet)


class Add(ActionWithOneDevice):
    __doc__ = m.Add.__doc__


class Remove(ActionWithOneDevice):
    __doc__ = m.Remove.__doc__


class Allocate(ActionWithMultipleDevices):
    __doc__ = m.Allocate.__doc__
    to = NestedOn(s_user.User,
                  description='The user the devices are allocated to.')
    organization = SanitizedStr(validate=Length(max=STR_SIZE),
                                description='The organization where the '
                                            'user was when this happened.')


class Deallocate(ActionWithMultipleDevices):
    __doc__ = m.Deallocate.__doc__
    from_rel = Nested(s_user.User,
                      data_key='from',
                      description='The user where the devices are not allocated to anymore.')
    organization = SanitizedStr(validate=Length(max=STR_SIZE),
                                description='The organization where the '
                                            'user was when this happened.')


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
    cycle_count = Integer(data_key='cycleCount', description=m.MeasureBattery.cycle_count.comment)
    health = EnumField(enums.BatteryHealth, description=m.MeasureBattery.health.comment)


class TestDataStorage(Test):
    __doc__ = m.TestDataStorage.__doc__
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)
    length = EnumField(TestDataStorageLength, required=True)
    status = SanitizedStr(lower=True, validate=Length(max=STR_SIZE), required=True)
    lifetime = TimeDelta(precision=TimeDelta.HOURS)
    assessment = Boolean()
    reallocated_sector_count = Integer(data_key='reallocatedSectorCount')
    power_cycle_count = Integer(data_key='powerCycleCount')
    reported_uncorrectable_errors = Integer(data_key='reportedUncorrectableErrors')
    command_timeout = Integer(data_key='commandTimeout')
    current_pending_sector_count = Integer(data_key='currentPendingSectorCount')
    offline_uncorrectable = Integer(data_key='offlineUncorrectable')
    remaining_lifetime_percentage = Integer(data_key='remainingLifetimePercentage')


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
    appearance_range = EnumField(AppearanceRange, required=True, data_key='appearanceRange')
    functionality_range = EnumField(FunctionalityRange,
                                    required=True,
                                    data_key='functionalityRange')
    labelling = Boolean()


class Rate(ActionWithOneDevice):
    __doc__ = m.Rate.__doc__
    rating = Integer(validate=Range(*R_POSITIVE),
                     dump_only=True,
                     description=m.Rate._rating.comment)
    version = Version(dump_only=True,
                      description=m.Rate.version.comment)
    appearance = Integer(validate=Range(enums.R_NEGATIVE),
                         dump_only=True,
                         description=m.Rate._appearance.comment)
    functionality = Integer(validate=Range(enums.R_NEGATIVE),
                            dump_only=True,
                            description=m.Rate._functionality.comment)
    rating_range = EnumField(RatingRange,
                             dump_only=True,
                             data_key='ratingRange',
                             description=m.Rate.rating_range.__doc__)


class RateComputer(Rate):
    __doc__ = m.RateComputer.__doc__
    processor = Float(dump_only=True)
    ram = Float(dump_only=True)
    data_storage = Float(dump_only=True, data_key='dataStorage')
    graphic_card = Float(dump_only=True, data_key='graphicCard')

    data_storage_range = EnumField(RatingRange, dump_only=True, data_key='dataStorageRange')
    ram_range = EnumField(RatingRange, dump_only=True, data_key='ramRange')
    processor_range = EnumField(RatingRange, dump_only=True, data_key='processorRange')
    graphic_card_range = EnumField(RatingRange, dump_only=True, data_key='graphicCardRange')


class Price(ActionWithOneDevice):
    __doc__ = m.Price.__doc__
    currency = EnumField(Currency, required=True, description=m.Price.currency.comment)
    price = Decimal(places=m.Price.SCALE,
                    rounding=m.Price.ROUND,
                    required=True,
                    description=m.Price.price.comment)
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
    name = SanitizedStr(validate=Length(min=4, max=STR_BIG_SIZE),
                        required=True,
                        description='The name of the OS installed.')
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
    software = EnumField(SnapshotSoftware,
                         required=True,
                         description='The software that generated this Snapshot.')
    version = Version(required=True, description='The version of the software.')
    actions = NestedOn(Action, many=True, dump_only=True)
    elapsed = TimeDelta(precision=TimeDelta.SECONDS)
    components = NestedOn(s_device.Component,
                          many=True,
                          description='A list of components that are inside of the device'
                                      'at the moment of this Snapshot.'
                                      'Order is preserved, so the component num 0 when'
                                      'submitting is the component num 0 when returning it back.')

    @validates_schema
    def validate_workbench_version(self, data: dict):
        if data['software'] == SnapshotSoftware.Workbench:
            if data['version'] < app.config['MIN_WORKBENCH']:
                raise ValidationError(
                    'Min. supported Workbench version is '
                    '{} but yours is {}.'.format(app.config['MIN_WORKBENCH'], data['version']),
                    field_names=['version']
                )

    @validates_schema
    def validate_components_only_workbench(self, data: dict):
        if data['software'] != SnapshotSoftware.Workbench:
            if data.get('components', None) is not None:
                raise ValidationError('Only Workbench can add component info',
                                      field_names=['components'])

    @validates_schema
    def validate_only_workbench_fields(self, data: dict):
        """Ensures workbench has ``elapsed`` and ``uuid`` and no others."""
        # todo test
        if data['software'] == SnapshotSoftware.Workbench:
            if not data.get('uuid', None):
                raise ValidationError('Snapshots from Workbench must have uuid',
                                      field_names=['uuid'])
            if data.get('elapsed', None) is None:
                raise ValidationError('Snapshots from Workbench must have elapsed',
                                      field_names=['elapsed'])
        else:
            if data.get('uuid', None):
                raise ValidationError('Only Snapshots from Workbench can have uuid',
                                      field_names=['uuid'])
            if data.get('elapsed', None):
                raise ValidationError('Only Snapshots from Workbench can have elapsed',
                                      field_names=['elapsed'])


class ToRepair(ActionWithMultipleDevices):
    __doc__ = m.ToRepair.__doc__


class Repair(ActionWithMultipleDevices):
    __doc__ = m.Repair.__doc__


class Available(ActionWithMultipleDevices):
    __doc__ = m.Available.__doc__


class ToPrepare(ActionWithMultipleDevices):
    __doc__ = m.ToPrepare.__doc__


class Prepare(ActionWithMultipleDevices):
    __doc__ = m.Prepare.__doc__


class Live(ActionWithOneDevice):
    __doc__ = m.Live.__doc__
    ip = IP(dump_only=True)
    subdivision_confidence = Integer(dump_only=True, data_key='subdivisionConfidence')
    subdivision = EnumField(Subdivision, dump_only=True)
    country = EnumField(Country, dump_only=True)
    city = SanitizedStr(lower=True, dump_only=True)
    city_confidence = Integer(dump_only=True, data_key='cityConfidence')
    isp = SanitizedStr(lower=True, dump_only=True)
    organization = SanitizedStr(lower=True, dump_only=True)
    organization_type = SanitizedStr(lower=True, dump_only=True, data_key='organizationType')


class Organize(ActionWithMultipleDevices):
    __doc__ = m.Organize.__doc__


class Reserve(Organize):
    __doc__ = m.Reserve.__doc__


class CancelReservation(Organize):
    __doc__ = m.CancelReservation.__doc__


class Trade(ActionWithMultipleDevices):
    __doc__ = m.Trade.__doc__
    shipping_date = DateTime(data_key='shippingDate')
    invoice_number = SanitizedStr(validate=Length(max=STR_SIZE), data_key='invoiceNumber')
    price = NestedOn(Price)
    to = NestedOn(s_agent.Agent, only_query='id', required=True, comment=m.Trade.to_comment)
    confirms = NestedOn(Organize)


class Sell(Trade):
    __doc__ = m.Sell.__doc__


class Donate(Trade):
    __doc__ = m.Donate.__doc__


class Rent(Trade):
    __doc__ = m.Rent.__doc__


class CancelTrade(Trade):
    __doc__ = m.CancelTrade.__doc__


class ToDisposeProduct(Trade):
    __doc__ = m.ToDisposeProduct.__doc__


class DisposeProduct(Trade):
    __doc__ = m.DisposeProduct.__doc__


class Receive(ActionWithMultipleDevices):
    __doc__ = m.Receive.__doc__
    role = EnumField(ReceiverRole)


class Migrate(ActionWithMultipleDevices):
    __doc__ = m.Migrate.__doc__
    other = URL()


class MigrateTo(Migrate):
    __doc__ = m.MigrateTo.__doc__


class MigrateFrom(Migrate):
    __doc__ = m.MigrateFrom.__doc__
