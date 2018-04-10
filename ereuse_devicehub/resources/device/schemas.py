from marshmallow.fields import Float, Integer, Nested, Str
from marshmallow.validate import Length, Range

from ereuse_devicehub.resources.model import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schema import Thing


class Device(Thing):
    id = Str(dump_only=True)
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
    serial_number = Str(load_from='serialNumber', dump_to='serialNumber')
    product_id = Str(load_from='productId', dump_to='productId')
    weight = Float(validate=Range(0.1, 3))
    width = Float(validate=Range(0.1, 3))
    height = Float(validate=Range(0.1, 3))
    events = Nested('Event', many=True, dump_only=True, only='id')


class Computer(Device):
    components = Nested('Component', many=True, dump_only=True, only='id')
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
    parent = Nested(Device, dump_only=True)


class GraphicCard(Component):
    memory = Integer(validate=Range(0, 10000))


class HardDrive(Component):
    size = Integer(validate=Range(0, 10 ** 8))
    erasure = Nested('EraseBasic', load_only=True)
    erasures = Nested('EraseBasic', dump_only=True, many=True)
    tests = Nested('TestHardDrive', many=True)
    benchmarks = Nested('BenchmarkHardDrive', many=True)


class Motherboard(Component):
    slots = Integer(validate=Range(1, 20), description='PCI slots the motherboard has.')
    usb = Integer(validate=Range(0, 20))
    firewire = Integer(validate=Range(0, 20))
    serial = Integer(validate=Range(0, 20))
    pcmcia = Integer(validate=Range(0, 20))


class NetworkAdapter(Component):
    speed = Integer(validate=Range(min=10, max=10000))
