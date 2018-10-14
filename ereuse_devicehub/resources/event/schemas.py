import decimal

from flask import current_app as app
from marshmallow import Schema as MarshmallowSchema, ValidationError, validates_schema
from marshmallow.fields import Boolean, DateTime, Decimal, Float, Integer, List, Nested, String, \
    TimeDelta, UUID
from marshmallow.validate import Length, Range
from sqlalchemy.util import OrderedSet
from teal.enums import Country, Currency, Subdivision
from teal.marshmallow import EnumField, IP, SanitizedStr, URL, Version
from teal.resource import Schema

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.agent.schemas import Agent
from ereuse_devicehub.resources.device.schemas import Component, Computer, Device
from ereuse_devicehub.resources.enums import AppearanceRange, Bios, FunctionalityRange, \
    PriceSoftware, RATE_POSITIVE, RatingSoftware, ReceiverRole, SnapshotExpectedEvents, \
    SnapshotSoftware, TestDataStorageLength
from ereuse_devicehub.resources.event import models as m
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.user.schemas import User


class Event(Thing):
    id = UUID(dump_only=True)
    name = SanitizedStr(default='',
                        validate=Length(max=STR_BIG_SIZE),
                        description=m.Event.name.comment)
    incidence = Boolean(default=False, description=m.Event.incidence.comment)
    closed = Boolean(missing=True, description=m.Event.closed.comment)
    error = Boolean(default=False, description=m.Event.error.comment)
    description = SanitizedStr(default='', description=m.Event.description.comment)
    start_time = DateTime(data_key='startTime', description=m.Event.start_time.comment)
    end_time = DateTime(data_key='endTime', description=m.Event.end_time.comment)
    snapshot = NestedOn('Snapshot', dump_only=True)
    agent = NestedOn(Agent, description=m.Event.agent_id.comment)
    author = NestedOn(User, dump_only=True, exclude=('token',))
    components = NestedOn(Component, dump_only=True, many=True)
    parent = NestedOn(Computer, dump_only=True, description=m.Event.parent_id.comment)
    url = URL(dump_only=True, description=m.Event.url.__doc__)


class EventWithOneDevice(Event):
    device = NestedOn(Device, only_query='id')


class EventWithMultipleDevices(Event):
    devices = NestedOn(Device, many=True, only_query='id', collection_class=OrderedSet)


class Add(EventWithOneDevice):
    pass


class Remove(EventWithOneDevice):
    pass


class Allocate(EventWithMultipleDevices):
    to = NestedOn(User,
                  description='The user the devices are allocated to.')
    organization = SanitizedStr(validate=Length(max=STR_SIZE),
                                description='The organization where the '
                                            'user was when this happened.')


class Deallocate(EventWithMultipleDevices):
    from_rel = Nested(User,
                      data_key='from',
                      description='The user where the devices are not allocated to anymore.')
    organization = SanitizedStr(validate=Length(max=STR_SIZE),
                                description='The organization where the '
                                            'user was when this happened.')


class EraseBasic(EventWithOneDevice):
    zeros = Boolean(required=True, description=m.EraseBasic.zeros.comment)
    steps = NestedOn('Step', many=True, required=True)


class EraseSectors(EraseBasic):
    pass


class Step(Schema):
    type = String(description='Only required when it is nested.')
    start_time = DateTime(required=True, data_key='startTime')
    end_time = DateTime(required=True, data_key='endTime')
    error = Boolean(default=False, description='Did the event fail?')


class StepZero(Step):
    pass


class StepRandom(Step):
    pass


class Rate(EventWithOneDevice):
    rating = Integer(validate=Range(*RATE_POSITIVE),
                     dump_only=True,
                     data_key='rating',
                     description='The rating for the content.')
    software = EnumField(RatingSoftware,
                         dump_only=True,
                         description='The algorithm used to produce this rating.')
    version = Version(dump_only=True,
                      description='The version of the software.')
    appearance = Integer(validate=Range(-3, 5), dump_only=True)
    functionality = Integer(validate=Range(-3, 5),
                            dump_only=True,
                            data_key='functionalityScore')


class IndividualRate(Rate):
    pass


class PhotoboxRate(IndividualRate):
    num = Integer(dump_only=True)
    # todo Image


class PhotoboxUserRate(IndividualRate):
    assembling = Integer()
    parts = Integer()
    buttons = Integer()
    dents = Integer()
    decolorization = Integer()
    scratches = Integer()
    tag_adhesive = Integer()
    dirt = Integer()


class PhotoboxSystemRate(IndividualRate):
    pass


class ManualRate(IndividualRate):
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
    processor = Float()
    ram = Float()
    data_storage = Float()
    graphic_card = Float()
    bios = Float()
    bios_range = EnumField(Bios,
                           description=m.WorkbenchRate.bios_range.comment,
                           data_key='biosRange')


class AggregateRate(Rate):
    workbench = NestedOn(WorkbenchRate, dump_only=True)
    manual = NestedOn(ManualRate, dump_only=True)
    processor = Float(dump_only=True)
    ram = Float(dump_only=True)
    data_storage = Float(dump_only=True)
    graphic_card = Float(dump_only=True)
    bios = EnumField(Bios, dump_only=True)


class Price(EventWithOneDevice):
    currency = EnumField(Currency, required=True)
    price = Decimal(places=4, rounding=decimal.ROUND_HALF_EVEN, required=True)
    software = EnumField(PriceSoftware, dump_only=True)
    version = Version(dump_only=True)
    rating = NestedOn(AggregateRate, dump_only=True)


class EreusePrice(Price):
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
    name = SanitizedStr(validate=Length(min=4, max=STR_BIG_SIZE),
                        required=True,
                        description='The name of the OS installed.')
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)


class Snapshot(EventWithOneDevice):
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
    components = NestedOn(Component,
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
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)


class TestDataStorage(Test):
    length = EnumField(TestDataStorageLength, required=True)
    status = SanitizedStr(lower=True, validate=Length(max=STR_SIZE), required=True)
    lifetime = TimeDelta(precision=TimeDelta.DAYS)
    assessment = Boolean()
    reallocated_sector_count = Integer(data_key='reallocatedSectorCount')
    power_cycle_count = Integer(data_key='powerCycleCount')
    reported_uncorrectable_errors = Integer(data_key='reportedUncorrectableErrors')
    command_timeout = Integer(data_key='commandTimeout')
    current_pending_sector_count = Integer(data_key='currentPendingSectorCount')
    offline_uncorrectable = Integer(data_key='offlineUncorrectable')
    remaining_lifetime_percentage = Integer(data_key='remainingLifetimePercentage')


class StressTest(Test):
    pass


class Benchmark(EventWithOneDevice):
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)


class BenchmarkDataStorage(Benchmark):
    read_speed = Float(required=True, data_key='readSpeed')
    write_speed = Float(required=True, data_key='writeSpeed')


class BenchmarkWithRate(Benchmark):
    rate = Integer(required=True)


class BenchmarkProcessor(BenchmarkWithRate):
    pass


class BenchmarkProcessorSysbench(BenchmarkProcessor):
    pass


class BenchmarkRamSysbench(BenchmarkWithRate):
    pass


class ToRepair(EventWithMultipleDevices):
    pass


class Repair(EventWithMultipleDevices):
    pass


class ReadyToUse(EventWithMultipleDevices):
    pass


class ToPrepare(EventWithMultipleDevices):
    pass


class Prepare(EventWithMultipleDevices):
    pass


class Live(EventWithOneDevice):
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
    pass


class Reserve(Organize):
    pass


class CancelReservation(Organize):
    pass


class Trade(EventWithMultipleDevices):
    shipping_date = DateTime(data_key='shippingDate')
    invoice_number = SanitizedStr(validate=Length(max=STR_SIZE), data_key='invoiceNumber')
    price = NestedOn(Price)
    to = NestedOn(Agent, only_query='id', required=True, comment=m.Trade.to_comment)
    confirms = NestedOn(Organize)


class Sell(Trade):
    pass


class Donate(Trade):
    pass


class Rent(Trade):
    pass


class CancelTrade(Trade):
    pass


class ToDisposeProduct(Trade):
    pass


class DisposeProduct(Trade):
    pass


class Receive(EventWithMultipleDevices):
    role = EnumField(ReceiverRole)


class Migrate(EventWithMultipleDevices):
    other = URL()


class MigrateTo(Migrate):
    pass


class MigrateFrom(Migrate):
    pass
