from flask import current_app as app
from marshmallow import ValidationError, validates_schema
from marshmallow.fields import Boolean, DateTime, Float, Integer, List, Nested, String, TimeDelta, \
    UUID
from marshmallow.validate import Length, Range

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.device.schemas import Component, Device
from ereuse_devicehub.resources.enums import AppearanceRange, Bios, FunctionalityRange, \
    RATE_POSITIVE, RatingSoftware, SnapshotExpectedEvents, SnapshotSoftware, TestHardDriveLength
from ereuse_devicehub.resources.event import models as m
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.user.schemas import User
from teal.marshmallow import EnumField, Version
from teal.resource import Schema


class Event(Thing):
    id = UUID(dump_only=True)
    name = String(default='',
                  validate=Length(STR_BIG_SIZE),
                  description=m.Event.name.comment.strip())
    date = DateTime('iso', description=m.Event.date.comment.strip())
    error = Boolean(default=False, description=m.Event.error.comment.strip())
    incidence = Boolean(default=False, description=m.Event.incidence.comment.strip())
    snapshot = NestedOn('Snapshot', dump_only=True)
    components = NestedOn(Component, dump_only=True, many=True)
    description = String(default='', description=m.Event.description.comment.strip())
    author = NestedOn(User, dump_only=True, exclude=('token',))
    closed = Boolean(missing=True, description=m.Event.closed.comment.strip())


class EventWithOneDevice(Event):
    device = NestedOn(Device)


class EventWithMultipleDevices(Event):
    devices = NestedOn(Device, many=True)


class Add(EventWithOneDevice):
    pass


class Remove(EventWithOneDevice):
    pass


class Allocate(EventWithMultipleDevices):
    to = NestedOn(User,
                  description='The user the devices are allocated to.')
    organization = String(validate=Length(STR_SIZE),
                          description='The organization where the user was when this happened.')


class Deallocate(EventWithMultipleDevices):
    from_rel = Nested(User,
                      data_key='from',
                      description='The user where the devices are not allocated to anymore.')
    organization = String(validate=Length(STR_SIZE),
                          description='The organization where the user was when this happened.')


class EraseBasic(EventWithOneDevice):
    start_time = DateTime(required=True, data_key='startTime')
    end_time = DateTime(required=True, data_key='endTime')
    secure_random_steps = Integer(validate=Range(min=0), required=True,
                                  data_key='secureRandomSteps')
    clean_with_zeros = Boolean(required=True, data_key='cleanWithZeros')
    steps = NestedOn('Step', many=True, required=True)


class EraseSectors(EraseBasic):
    pass


class Step(Schema):
    type = String(description='Only required when it is nested.')
    start_time = DateTime(required=True, data_key='startTime')
    end_time = DateTime(required=True, data_key='endTime')
    secure_random_steps = Integer(validate=Range(min=0),
                                  required=True,
                                  data_key='secureRandomSteps')
    clean_with_zeros = Boolean(required=True, data_key='cleanWithZeros')
    error = Boolean(default=False, description='Did the event fail?')


class StepZero(Step):
    pass


class StepRandom(Step):
    pass


class Rate(EventWithOneDevice):
    rating = Integer(validate=Range(*RATE_POSITIVE),
                     dump_only=True,
                     data_key='ratingValue',
                     description='The rating for the content.')
    algorithm_software = EnumField(RatingSoftware,
                                   dump_only=True,
                                   data_key='algorithmSoftware',
                                   description='The algorithm used to produce this rating.')
    algorithm_version = Version(dump_only=True,
                                data_key='algorithmVersion',
                                description='The algorithm_version of the algorithm_software.')
    appearance = Integer(validate=Range(-3, 5), dump_only=True)
    functionality = Integer(validate=Range(-3, 5),
                            dump_only=True,
                            data_key='functionalityScore')


class IndividualRate(Rate):
    pass


class AggregateRate(Rate):
    ratings = NestedOn(IndividualRate, many=True)


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
                                 description='Grades the imperfections that aesthetically '
                                             'affect the device, but not its usage.')
    functionality_range = EnumField(FunctionalityRange,
                                    required=True,
                                    data_key='functionalityRange',
                                    description='Grades the defects of a device that affect its usage.')
    labelling = Boolean(description='Sets if there are labels stuck that should be removed.')


class AppRate(ManualRate):
    pass


class WorkbenchRate(ManualRate):
    processor = Float()
    ram = Float()
    data_storage = Float()
    graphic_card = Float()
    bios = EnumField(Bios, description='How difficult it has been to set the bios to '
                                       'boot from the network.')


class Install(EventWithOneDevice):
    name = String(validate=Length(min=4, max=STR_BIG_SIZE),
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

    device = NestedOn(Device)
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
                    'Min. supported Workbench algorithm_version is '
                    '{}'.format(app.config['MIN_WORKBENCH']),
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
            if not data.get('elapsed', None):
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
    length = EnumField(TestHardDriveLength, required=True)
    status = String(validate=Length(max=STR_SIZE), required=True)
    lifetime = TimeDelta(precision=TimeDelta.DAYS, required=True)
    first_error = Integer(missing=0, data_key='firstError')
    passed_lifetime = TimeDelta(precision=TimeDelta.DAYS, data_key='passedLifetime')
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
    elapsed = TimeDelta(precision=TimeDelta.SECONDS)


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
