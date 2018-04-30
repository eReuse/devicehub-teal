from flask import current_app as app
from marshmallow import ValidationError, post_load, validates_schema
from marshmallow.fields import Boolean, DateTime, Integer, Nested, String, TimeDelta, UUID
from marshmallow.validate import Length, Range
from marshmallow_enum import EnumField

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.device.schemas import Component, Device
from ereuse_devicehub.resources.event.enums import Appearance, Bios, Functionality, Orientation, \
    SoftwareType, StepTypes, TestHardDriveLength
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.user.schemas import User
from teal.marshmallow import Color, Version
from teal.resource import Schema


class Event(Thing):
    id = Integer(dump_only=True)
    title = String(default='',
                   validate=Length(STR_BIG_SIZE),
                   description='A name or title for the event. Used when searching for events.')
    date = DateTime('iso', description='When this event happened. '
                                       'Leave it blank if it is happening now. '
                                       'This is used when creating events retroactively.')
    secured = Boolean(default=False,
                      description='Can we ensure the info in this event is totally correct?'
                                  'Devicehub will automatically set this too for some events,'
                                  'for example in snapshots if it could detect the ids of the'
                                  'hardware without margin of doubt.')
    incidence = Boolean(default=False,
                        description='Was something wrong in this event?')
    snapshot = Nested('Snapshot', dump_only=True, only='id')
    description = String(default='', description='A comment about the event.')
    components = Nested(Component, dump_only=True, only='id', many=True)


class EventWithOneDevice(Event):
    device = Nested(Device, only='id')


class EventWithMultipleDevices(Event):
    device = Nested(Device, many=True, only='id')


class Add(EventWithOneDevice):
    pass


class Remove(EventWithOneDevice):
    pass


class Allocate(EventWithMultipleDevices):
    to = Nested(User, only='id',
                description='The user the devices are allocated to.')
    organization = String(validate=Length(STR_SIZE),
                          description='The organization where the user was when this happened.')


class Deallocate(EventWithMultipleDevices):
    from_rel = Nested(User, only='id',
                      data_key='from',
                      description='The user where the devices are not allocated to anymore.')
    organization = String(validate=Length(STR_SIZE),
                          description='The organization where the user was when this happened.')


class EraseBasic(EventWithOneDevice):
    starting_time = DateTime(required=True, data_key='startingTime')
    ending_time = DateTime(required=True, data_key='endingTime')
    secure_random_steps = Integer(validate=Range(min=0), required=True,
                                  data_key='secureRandomSteps')
    success = Boolean(required=True)
    clean_with_zeros = Boolean(required=True, data_key='cleanWithZeros')


class EraseSectors(EraseBasic):
    pass


class Step(Schema):
    id = Integer(dump_only=True)
    type = EnumField(StepTypes, required=True)
    starting_time = DateTime(required=True, data_key='startingTime')
    ending_time = DateTime(required=True, data_key='endingTime')
    secure_random_steps = Integer(validate=Range(min=0),
                                  required=True,
                                  data_key='secureRandomSteps')
    success = Boolean(required=True)
    clean_with_zeros = Boolean(required=True, data_key='cleanWithZeros')


class Condition(Schema):
    appearance = EnumField(Appearance,
                           required=True,
                           description='Grades the imperfections that aesthetically '
                                       'affect the device, but not its usage.')
    appearance_score = Integer(validate=Range(-3, 5), dump_only=True)
    functionality = EnumField(Functionality,
                              required=True,
                              description='Grades the defects of a device that affect its usage.')
    functionality_score = Integer(validate=Range(-3, 5),
                                  dump_only=True,
                                  data_key='functionalityScore')
    labelling = Boolean(description='Sets if there are labels stuck that should be removed.')
    bios = EnumField(Bios, description='How difficult it has been to set the bios to '
                                       'boot from the network.')
    general = Integer(dump_only=True,
                      validate=Range(0, 5),
                      description='The grade of the device.')


class Installation(Schema):
    name = String(validate=Length(STR_BIG_SIZE),
                  required=True,
                  description='The name of the OS installed.')
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)
    success = Boolean(required=True)


class Inventory(Schema):
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)


class Snapshot(EventWithOneDevice):
    device = NestedOn(Device)  # todo and when dumping?
    components = NestedOn(Component, many=True)
    uuid = UUID(required=True)
    version = Version(required=True, description='The version of the SnapshotSoftware.')
    software = EnumField(SoftwareType,
                         required=True,
                         description='The software that generated this Snapshot.')
    condition = Nested(Condition, required=True)
    install = Nested(Installation)
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)
    inventory = Nested(Inventory)
    color = Color(description='Main color of the device.')
    orientation = EnumField(Orientation, description='Is the device main stand wider or larger?')
    force_creation = Boolean(data_key='forceCreation')

    @validates_schema
    def validate_workbench_version(self, data: dict):
        if data['software'] == SoftwareType.Workbench:
            if data['version'] < app.config['MIN_WORKBENCH']:
                raise ValidationError(
                    'Min. supported Workbench version is {}'.format(app.config['MIN_WORKBENCH']),
                    field_names=['version']
                )

    @validates_schema
    def validate_components_only_workbench(self, data: dict):
        if data['software'] != SoftwareType.Workbench:
            if data['components'] is not None:
                raise ValidationError('Only Workbench can add component info',
                                      field_names=['components'])

    @post_load
    def normalize_nested(self, data: dict):
        data.update(data.pop('condition'))
        data['condition'] = data.pop('general', None)
        data.update({'install_' + key: value for key, value in data.pop('install', {})})
        data['inventory_elapsed'] = data.get('inventory', {}).pop('elapsed', None)
        return data


class Test(EventWithOneDevice):
    elapsed = TimeDelta(precision=TimeDelta.SECONDS, required=True)
    success = Boolean(required=True)


class TestHardDrive(Test):
    length = EnumField(TestHardDriveLength, required=True)
    status = String(validate=Length(max=STR_SIZE), required=True)
    lifetime = TimeDelta(precision=TimeDelta.DAYS, required=True)
    first_error = Integer()


class StressTest(Test):
    pass
