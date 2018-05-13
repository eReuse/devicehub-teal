from marshmallow.fields import Float, Integer, Str
from marshmallow.validate import Length, OneOf, Range

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing, UnitCodes


class Device(Thing):
    id = Integer(dump_only=True,
                 description='The identifier of the device for this database.')
    hid = Str(dump_only=True,
              description='The Hardware ID is the unique ID traceability systems '
                          'use to ID a device globally.')
    pid = Str(description='The PID identifies a device under a circuit or platform.',
              validate=Length(max=STR_SIZE))
    gid = Str(description='The Giver ID links the device to the giver\'s (donor, seller)'
                          'internal inventory.',
              validate=Length(max=STR_SIZE))
    model = Str(validate=Length(max=STR_BIG_SIZE))
    manufacturer = Str(validate=Length(max=STR_SIZE))
    serial_number = Str(data_key='serialNumber')
    product_id = Str(data_key='productId')
    weight = Float(validate=Range(0.1, 3),
                   unit=UnitCodes.kgm,
                   description='The weight of the device in Kgm.')
    width = Float(validate=Range(0.1, 3),
                  unit=UnitCodes.m,
                  description='The width of the device in meters.')
    height = Float(validate=Range(0.1, 3),
                   unit=UnitCodes.m,
                   description='The height of the device in meters.')
    events = NestedOn('Event', many=True, dump_only=True)


class Computer(Device):
    components = NestedOn('Component', many=True, dump_only=True)
    pass


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


class Component(Device):
    parent = NestedOn(Device, dump_only=True)


class GraphicCard(Component):
    memory = Integer(validate=Range(0, 10000),
                     unit=UnitCodes.mbyte,
                     description='The amount of memory of the Graphic Card in MB.')


class HardDrive(Component):
    size = Integer(validate=Range(0, 10 ** 8),
                   unit=UnitCodes.mbyte,
                   description='The size of the hard-drive in MB.')
    erasure = NestedOn('EraseBasic', load_only=True)
    tests = NestedOn('TestHardDrive', many=True, load_only=True)
    benchmarks = NestedOn('BenchmarkHardDrive', load_only=True, many=True)


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
