from flask import current_app as app
from marshmallow import ValidationError, validates_schema
from marshmallow.fields import Boolean, DateTime, Float, Integer, Nested, String, TimeDelta, UUID
from marshmallow.validate import Length, Range
from marshmallow_enum import EnumField

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.device.schemas import Component, Device
from ereuse_devicehub.resources.enums import AppearanceRange, Bios, FunctionalityRange, \
    RATE_POSITIVE, RatingSoftware, SnapshotExpectedEvents, SnapshotSoftware, TestHardDriveLength
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.user.schemas import User
from teal.marshmallow import Version
from teal.resource import Schema


class Event(Thing):
    id = Integer(dump_only=True)
    title = String(default='',
                   validate=Length(STR_BIG_SIZE),
                   description='A name or title for the event. Used when searching for events.')
    date = DateTime('iso', description='When this event happened. '
                                       'Leave it blank if it is happening now. '
                                       'This is used when creating events retroactively.')
    error = Boolean(default=False, description='Did the event fail?')
    incidence = Boolean(default=False,
                        description='Should this event be reviewed due some anomaly?')
    snapshot = NestedOn('Snapshot', dump_only=True)
    components = NestedOn(Component, dump_only=True, many=True)
    description = String(default='', description='A comment about the event.')


class EventWithOneDevice(Event):
    device = NestedOn(Device, only='id')


class EventWithMultipleDevices(Event):
    devices = NestedOn(Device, many=True, only='id')


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
    id = Integer(dump_only=True)
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


class PhotoboxUserRate(PhotoboxRate):
    assembling = Integer()
    parts = Integer()
    buttons = Integer()
    dents = Integer()
    decolorization = Integer()
    scratches = Integer()
    tag_adhesive = Integer()
    dirt = Integer()


class PhotoboxSystemRate(PhotoboxRate):
    pass


class WorkbenchRate(IndividualRate):
    processor = Float()
    ram = Float()
    data_storage = Float()
    graphic_card = Float()
    labelling = Boolean(description='Sets if there are labels stuck that should be removed.')
    bios = EnumField(Bios, description='How difficult it has been to set the bios to '
                                       'boot from the network.')
    appearance_range = EnumField(AppearanceRange,
                                 required=True,
                                 data_key='appearanceRange',
                                 description='Grades the imperfections that aesthetically '
                                             'affect the device, but not its usage.')
    functionality_range = EnumField(FunctionalityRange,
                                    required=True,
                                    data_key='functionalityRange',
                                    description='Grades the defects of a device that affect its usage.')


class Install(EventWithOneDevice):
    name = String(validate=Length(STR_BIG_SIZE),
                  required=True,
                  description='The name of the OS installed.')
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)


class Snapshot(EventWithOneDevice):
    """
    The Snapshot updates the state of the device with information about
    its components and events performed at them.

    See docs for more info.
    """
    uuid = UUID(required=True)
    software = EnumField(SnapshotSoftware,
                         required=True,
                         description='The software that generated this Snapshot.')
    version = Version(required=True, description='The version of the software.')
    events = NestedOn(Event, many=True)  # todo ensure only specific events are submitted
    expected_events = EnumField(SnapshotExpectedEvents,
                                many=True,
                                data_key='expectedEvents',
                                description='Keep open this Snapshot until the following events'
                                            'are performed. Setting this value will activate'
                                            'the async Snapshot.')
    device = NestedOn(Device)
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)
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
            if data['components'] is not None:
                raise ValidationError('Only Workbench can add component info',
                                      field_names=['components'])


class Test(EventWithOneDevice):
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)


class TestDataStorage(Test):
    length = EnumField(TestHardDriveLength, required=True)
    status = String(validate=Length(max=STR_SIZE), required=True)
    lifetime = TimeDelta(precision=TimeDelta.DAYS, required=True)
    first_error = Integer()


class StressTest(Test):
    pass
