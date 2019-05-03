from flask import current_app as app
from marshmallow import Schema as MarshmallowSchema, ValidationError, fields as f, validates_schema
from marshmallow.fields import Boolean, DateTime, Decimal, Float, Integer, List, Nested, String, \
    TimeDelta, UUID
from marshmallow.validate import Length, OneOf, Range
from sqlalchemy.util import OrderedSet
from teal.enums import Country, Currency, Subdivision
from teal.marshmallow import EnumField, IP, SanitizedStr, URL, Version
from teal.resource import Schema

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources import enums
from ereuse_devicehub.resources.agent import schemas as s_agent
from ereuse_devicehub.resources.device import schemas as s_device
from ereuse_devicehub.resources.enums import AppearanceRange, Bios, FunctionalityRange, \
    PhysicalErasureMethod, PriceSoftware, RATE_POSITIVE, RatingRange, RatingSoftware, ReceiverRole, \
    Severity, SnapshotExpectedEvents, SnapshotSoftware, TestDataStorageLength
from ereuse_devicehub.resources.event import models as m
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.user import schemas as s_user


class Event(Thing):
    __doc__ = m.Event.__doc__
    id = UUID(dump_only=True)
    name = SanitizedStr(default='',
                        validate=Length(max=STR_BIG_SIZE),
                        description=m.Event.name.comment)
    closed = Boolean(missing=True, description=m.Event.closed.comment)
    severity = EnumField(Severity, description=m.Event.severity.comment)
    description = SanitizedStr(default='', description=m.Event.description.comment)
    start_time = DateTime(data_key='startTime', description=m.Event.start_time.comment)
    end_time = DateTime(data_key='endTime', description=m.Event.end_time.comment)
    snapshot = NestedOn('Snapshot', dump_only=True)
    agent = NestedOn(s_agent.Agent, description=m.Event.agent_id.comment)
    author = NestedOn(s_user.User, dump_only=True, exclude=('token',))
    components = NestedOn(s_device.Component, dump_only=True, many=True)
    parent = NestedOn(s_device.Computer, dump_only=True, description=m.Event.parent_id.comment)
    url = URL(dump_only=True, description=m.Event.url.__doc__)


class EventWithOneDevice(Event):
    __doc__ = m.EventWithOneDevice.__doc__
    device = NestedOn(s_device.Device, only_query='id')


class EventWithMultipleDevices(Event):
    __doc__ = m.EventWithMultipleDevices.__doc__
    devices = NestedOn(s_device.Device, many=True, only_query='id', collection_class=OrderedSet)


class Add(EventWithOneDevice):
    __doc__ = m.Add.__doc__


class Remove(EventWithOneDevice):
    __doc__ = m.Remove.__doc__


class Allocate(EventWithMultipleDevices):
    __doc__ = m.Allocate.__doc__
    to = NestedOn(s_user.User,
                  description='The user the devices are allocated to.')
    organization = SanitizedStr(validate=Length(max=STR_SIZE),
                                description='The organization where the '
                                            'user was when this happened.')


class Deallocate(EventWithMultipleDevices):
    __doc__ = m.Deallocate.__doc__
    from_rel = Nested(s_user.User,
                      data_key='from',
                      description='The user where the devices are not allocated to anymore.')
    organization = SanitizedStr(validate=Length(max=STR_SIZE),
                                description='The organization where the '
                                            'user was when this happened.')


class EraseBasic(EventWithOneDevice):
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
    severity = EnumField(Severity, description=m.Event.severity.comment)


class StepZero(Step):
    __doc__ = m.StepZero.__doc__


class StepRandom(Step):
    __doc__ = m.StepRandom.__doc__


class Rate(EventWithOneDevice):
    __doc__ = m.Rate.__doc__
    rating = Integer(validate=Range(*RATE_POSITIVE),
                     dump_only=True,
                     description=m.Rate.rating.comment)
    software = EnumField(RatingSoftware,
                         dump_only=True,
                         description=m.Rate.software.comment)
    version = Version(dump_only=True,
                      description=m.Rate.version.comment)
    appearance = Integer(validate=Range(-3, 5), dump_only=True)
    functionality = Integer(validate=Range(-3, 5), dump_only=True)
    rating_range = EnumField(RatingRange, dump_only=True, data_key='ratingRange')


class IndividualRate(Rate):
    __doc__ = m.IndividualRate.__doc__


class ManualRate(IndividualRate):
    __doc__ = m.ManualRate.__doc__
    appearance_range = EnumField(AppearanceRange,
                                 required=True,
                                 data_key='appearanceRange',
                                 description=m.ManualRate.appearance_range.comment)
    functionality_range = EnumField(FunctionalityRange,
                                    required=True,
                                    data_key='functionalityRange',
                                    description=m.ManualRate.functionality_range.comment)
    labelling = Boolean(description=m.ManualRate.labelling.comment)


class WorkbenchRate(ManualRate):
    __doc__ = m.WorkbenchRate.__doc__
    processor = Float()
    ram = Float()
    data_storage = Float()
    graphic_card = Float()
    bios = Float()
    bios_range = EnumField(Bios,
                           description=m.WorkbenchRate.bios_range.comment,
                           data_key='biosRange')
    data_storage_range = EnumField(RatingRange, dump_only=True, data_key='dataStorageRange')
    ram_range = EnumField(RatingRange, dump_only=True, data_key='ramRange')
    processor_range = EnumField(RatingRange, dump_only=True, data_key='processorRange')
    graphic_card_range = EnumField(RatingRange, dump_only=True, data_key='graphicCardRange')


class AggregateRate(Rate):
    __doc__ = m.AggregateRate.__doc__
    workbench = NestedOn(WorkbenchRate, dump_only=True,
                         description=m.AggregateRate.workbench_id.comment)
    manual = NestedOn(ManualRate,
                      dump_only=True,
                      description=m.AggregateRate.manual_id.comment)
    processor = Float(dump_only=True)
    ram = Float(dump_only=True)
    data_storage = Float(dump_only=True)
    graphic_card = Float(dump_only=True)
    bios = EnumField(Bios, dump_only=True)
    bios_range = EnumField(Bios,
                           description=m.WorkbenchRate.bios_range.comment,
                           data_key='biosRange')
    appearance_range = EnumField(AppearanceRange,
                                 required=True,
                                 data_key='appearanceRange',
                                 description=m.ManualRate.appearance_range.comment)
    functionality_range = EnumField(FunctionalityRange,
                                    required=True,
                                    data_key='functionalityRange',
                                    description=m.ManualRate.functionality_range.comment)
    labelling = Boolean(description=m.ManualRate.labelling.comment)
    data_storage_range = EnumField(RatingRange, dump_only=True, data_key='dataStorageRange')
    ram_range = EnumField(RatingRange, dump_only=True, data_key='ramRange')
    processor_range = EnumField(RatingRange, dump_only=True, data_key='processorRange')
    graphic_card_range = EnumField(RatingRange, dump_only=True, data_key='graphicCardRange')


class Price(EventWithOneDevice):
    __doc__ = m.Price.__doc__
    currency = EnumField(Currency, required=True, description=m.Price.currency.comment)
    price = Decimal(places=m.Price.SCALE,
                    rounding=m.Price.ROUND,
                    required=True,
                    description=m.Price.price.comment)
    software = EnumField(PriceSoftware, dump_only=True, description=m.Price.software.comment)
    version = Version(dump_only=True, description=m.Price.version.comment)
    rating = NestedOn(AggregateRate, dump_only=True, description=m.Price.rating_id.comment)


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


class Install(EventWithOneDevice):
    __doc__ = m.Install.__doc__
    name = SanitizedStr(validate=Length(min=4, max=STR_BIG_SIZE),
                        required=True,
                        description='The name of the OS installed.')
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)
    address = Integer(validate=OneOf({8, 16, 32, 64, 128, 256}))


class Snapshot(EventWithOneDevice):
    __doc__ = m.Snapshot.__doc__
    """
    The Snapshot updates the state of the device with information about
    its components and events performed at them.

    See docs for more info.
    """
    uuid = UUID()
    software = EnumField(SnapshotSoftware,
                         required=True,
                         description='The software that generated this Snapshot.')
    version = Version(required=True, description='The version of the software.')
    events = NestedOn(Event, many=True, dump_only=True)
    expected_events = List(EnumField(SnapshotExpectedEvents),
                           data_key='expectedEvents',
                           description='Keep open this Snapshot until the following events'
                                       'are performed. Setting this value will activate'
                                       'the async Snapshot.')

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


class Test(EventWithOneDevice):
    __doc__ = m.Test.__doc__
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)


class TestDataStorage(Test):
    __doc__ = m.TestDataStorage.__doc__
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


class MeasureBattery(Test):
    __doc__ = m.MeasureBattery.__doc__
    size = Integer(required=True, description=m.MeasureBattery.size.comment)
    voltage = Integer(required=True, description=m.MeasureBattery.voltage.comment)
    cycle_count = Integer(required=True, description=m.MeasureBattery.cycle_count.comment)
    health = EnumField(enums.BatteryHealth, description=m.MeasureBattery.health.comment)


class StressTest(Test):
    __doc__ = m.StressTest.__doc__


class Benchmark(EventWithOneDevice):
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


class ToRepair(EventWithMultipleDevices):
    __doc__ = m.ToRepair.__doc__


class Repair(EventWithMultipleDevices):
    __doc__ = m.Repair.__doc__


class ReadyToUse(EventWithMultipleDevices):
    __doc__ = m.ReadyToUse.__doc__


class ToPrepare(EventWithMultipleDevices):
    __doc__ = m.ToPrepare.__doc__


class Prepare(EventWithMultipleDevices):
    __doc__ = m.Prepare.__doc__


class Live(EventWithOneDevice):
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


class Organize(EventWithMultipleDevices):
    __doc__ = m.Organize.__doc__


class Reserve(Organize):
    __doc__ = m.Reserve.__doc__


class CancelReservation(Organize):
    __doc__ = m.CancelReservation.__doc__


class Trade(EventWithMultipleDevices):
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


class Receive(EventWithMultipleDevices):
    __doc__ = m.Receive.__doc__
    role = EnumField(ReceiverRole)


class Migrate(EventWithMultipleDevices):
    __doc__ = m.Migrate.__doc__
    other = URL()


class MigrateTo(Migrate):
    __doc__ = m.MigrateTo.__doc__


class MigrateFrom(Migrate):
    __doc__ = m.MigrateFrom.__doc__
