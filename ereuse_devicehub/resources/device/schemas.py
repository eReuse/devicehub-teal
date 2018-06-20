from marshmallow import post_load, pre_load
from marshmallow.fields import Float, Integer, Str
from marshmallow.validate import Length, OneOf, Range
from marshmallow_enum import EnumField
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.device import models as m
from ereuse_devicehub.resources.enums import ComputerMonitorTechnologies, RamFormat, RamInterface
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing, UnitCodes
from teal.marshmallow import ValidationError


class Device(Thing):
    id = Integer(description=m.Device.id, dump_only=True)
    hid = Str(dump_only=True, description=m.Device.hid)
    tags = NestedOn('Tag', many=True, collection_class=OrderedSet)
    model = Str(validate=Length(max=STR_BIG_SIZE))
    manufacturer = Str(validate=Length(max=STR_SIZE))
    serial_number = Str(data_key='serialNumber')
    product_id = Str(data_key='productId')
    weight = Float(validate=Range(0.1, 3), unit=UnitCodes.kgm, description=m.Device.weight)
    width = Float(validate=Range(0.1, 3), unit=UnitCodes.m, description=m.Device.width)
    height = Float(validate=Range(0.1, 3), unit=UnitCodes.m, description=m.Device.height)
    events = NestedOn('Event', many=True, dump_only=True)
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


class Desktop(Computer):
    pass


class Laptop(Computer):
    pass


class Netbook(Computer):
    pass


class Server(Computer):
    pass


class Microtower(Computer):
    pass


class ComputerMonitor(Device):
    size = Float(description=m.ComputerMonitor.size.comment, validate=Range(2, 150))
    technology = EnumField(ComputerMonitorTechnologies,
                           description=m.ComputerMonitor.technology.comment)
    resolution_width = Integer(data_key='resolutionWidth',
                               validate=Range(10, 20000),
                               description=m.ComputerMonitor.resolution_width.comment)
    resolution_height = Integer(data_key='resolutionHeight',
                                validate=Range(10, 20000),
                                description=m.ComputerMonitor.resolution_height.comment)


class Component(Device):
    parent = NestedOn(Device, dump_only=True)


class GraphicCard(Component):
    memory = Integer(validate=Range(0, 10000),
                     unit=UnitCodes.mbyte,
                     description='The amount of memory of the Graphic Card in MB.')


class DataStorage(Component):
    size = Integer(validate=Range(0, 10 ** 8),
                   unit=UnitCodes.mbyte,
                   description='The size of the hard-drive in MB.')
    erasure = NestedOn('EraseBasic', load_only=True)
    tests = NestedOn('TestHardDrive', many=True, load_only=True)
    benchmarks = NestedOn('BenchmarkHardDrive', load_only=True, many=True)


class HardDrive(DataStorage):
    pass


class SolidStateDrive(DataStorage):
    pass


class Motherboard(Component):
    slots = Integer(validate=Range(1, 20), description='PCI slots the motherboard has.')
    usb = Integer(validate=Range(0, 20))
    firewire = Integer(validate=Range(0, 20))
    serial = Integer(validate=Range(0, 20))
    pcmcia = Integer(validate=Range(0, 20))


class NetworkAdapter(Component):
    speed = Integer(validate=Range(min=10, max=10000),
                    unit=UnitCodes.mbps,
                    description='The maximum speed this network adapter can handle, in mbps.')


class Processor(Component):
    speed = Float(validate=Range(min=0.1, max=15), unit=UnitCodes.ghz)
    cores = Integer(validate=Range(min=1, max=10))  # todo from numberOfCores
    address = Integer(validate=OneOf({8, 16, 32, 64, 128, 256}))


class RamModule(Component):
    size = Integer(validate=Range(min=128, max=17000), unit=UnitCodes.mbyte)
    speed = Float(validate=Range(min=100, max=10000), unit=UnitCodes.mhz)
    interface = EnumField(RamInterface)
    format = EnumField(RamFormat)
