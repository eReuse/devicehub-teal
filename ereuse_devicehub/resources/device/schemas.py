from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.device import models as m
from ereuse_devicehub.resources.enums import ComputerChassis, DataStorageInterface, DisplayTech, \
    RamFormat, RamInterface
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing, UnitCodes
from marshmallow import post_load, pre_load
from marshmallow.fields import Float, Integer, Str
from marshmallow.validate import Length, OneOf, Range
from sqlalchemy.util import OrderedSet
from stdnum import imei, meid
from teal.marshmallow import EnumField, ValidationError


class Device(Thing):
    id = Integer(description=m.Device.id.comment, dump_only=True)
    hid = Str(dump_only=True, description=m.Device.hid.comment)
    tags = NestedOn('Tag',
                    many=True,
                    collection_class=OrderedSet,
                    description='The set of tags that identify the device.')
    model = Str(validate=Length(max=STR_BIG_SIZE))
    manufacturer = Str(validate=Length(max=STR_SIZE))
    serial_number = Str(data_key='serialNumber')
    weight = Float(validate=Range(0.1, 3), unit=UnitCodes.kgm, description=m.Device.weight.comment)
    width = Float(validate=Range(0.1, 3), unit=UnitCodes.m, description=m.Device.width.comment)
    height = Float(validate=Range(0.1, 3), unit=UnitCodes.m, description=m.Device.height.comment)
    events = NestedOn('Event', many=True, dump_only=True, description=m.Device.events.__doc__)
    events_one = NestedOn('Event', many=True, load_only=True, collection_class=OrderedSet)

    @pre_load
    def from_events_to_events_one(self, data: dict):
        """
        Not an elegant way of allowing submitting events to a device
        (in the context of Snapshots) without creating an ``events``
        field at the model (which is not possible).
        :param data:
        :return:
        """
        # Note that it is secure to allow uploading events_one
        # as the only time an user can send a device object is
        # in snapshots.
        data['events_one'] = data.pop('events', [])
        return data

    @post_load
    def validate_snapshot_events(self, data):
        """Validates that only snapshot-related events can be uploaded."""
        from ereuse_devicehub.resources.event.models import EraseBasic, Test, Rate, Install, \
            Benchmark
        for event in data['events_one']:
            if not isinstance(event, (Install, EraseBasic, Rate, Test, Benchmark)):
                raise ValidationError('You cannot upload {}'.format(event), field_names=['events'])


class Computer(Device):
    components = NestedOn('Component', many=True, dump_only=True, collection_class=OrderedSet)
    chassis = EnumField(ComputerChassis, required=True)


class Desktop(Computer):
    pass


class Laptop(Computer):
    pass


class Server(Computer):
    pass


class DisplayMixin:
    size = Float(description=m.DisplayMixin.size.comment, validate=Range(2, 150))
    technology = EnumField(DisplayTech,
                           description=m.DisplayMixin.technology.comment)
    resolution_width = Integer(data_key='resolutionWidth',
                               validate=Range(10, 20000),
                               description=m.DisplayMixin.resolution_width.comment)
    resolution_height = Integer(data_key='resolutionHeight',
                                validate=Range(10, 20000),
                                description=m.DisplayMixin.resolution_height.comment)


class NetworkMixin:
    speed = Integer(validate=Range(min=10, max=10000),
                    unit=UnitCodes.mbps,
                    description=m.NetworkAdapter.speed.comment)


class Monitor(DisplayMixin, Device):
    pass


class ComputerMonitor(Monitor):
    pass


class TelevisionSet(Monitor):
    pass


class Mobile(Device):
    imei = Integer(validate=lambda x: imei.validate(str(x)),
                   description=m.Mobile.imei.comment)
    meid = Str(validate=meid.validate, description=m.Mobile.meid.comment)

    @post_load
    def convert_meid(self, data: dict):
        if 'meid' in data:
            data['meid'] = meid.compact(data['meid'])


class Smartphone(Mobile):
    pass


class Tablet(Mobile):
    pass


class Cellphone(Mobile):
    pass


class Component(Device):
    parent = NestedOn(Device, dump_only=True)


class GraphicCard(Component):
    memory = Integer(validate=Range(0, 10000),
                     unit=UnitCodes.mbyte,
                     description=m.GraphicCard.memory.comment)


class DataStorage(Component):
    size = Integer(validate=Range(0, 10 ** 8),
                   unit=UnitCodes.mbyte,
                   description=m.DataStorage.size.comment)
    interface = EnumField(DataStorageInterface)


class HardDrive(DataStorage):
    pass


class SolidStateDrive(DataStorage):
    pass


class Motherboard(Component):
    slots = Integer(validate=Range(0, 20),
                    description=m.Motherboard.slots.comment)
    usb = Integer(validate=Range(0, 20))
    firewire = Integer(validate=Range(0, 20))
    serial = Integer(validate=Range(0, 20))
    pcmcia = Integer(validate=Range(0, 20))


class NetworkAdapter(NetworkMixin, Component):
    pass


class Processor(Component):
    speed = Float(validate=Range(min=0.1, max=15), unit=UnitCodes.ghz)
    cores = Integer(validate=Range(min=1, max=10))  # todo from numberOfCores
    address = Integer(validate=OneOf({8, 16, 32, 64, 128, 256}))


class RamModule(Component):
    size = Integer(validate=Range(min=128, max=17000), unit=UnitCodes.mbyte)
    speed = Float(validate=Range(min=100, max=10000), unit=UnitCodes.mhz)
    interface = EnumField(RamInterface)
    format = EnumField(RamFormat)


class SoundCard(Component):
    pass


class Display(DisplayMixin, Component):
    pass
