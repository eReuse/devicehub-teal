from marshmallow import post_load, pre_load
from marshmallow.fields import Boolean, DateTime, Float, Integer, List, Str, String
from marshmallow.validate import Length, OneOf, Range
from sqlalchemy.util import OrderedSet
from stdnum import imei, meid
from teal.enums import Layouts
from teal.marshmallow import EnumField, SanitizedStr, URL, ValidationError
from teal.resource import Schema

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources import enums
from ereuse_devicehub.resources.device import models as m, states
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing, UnitCodes


class Device(Thing):
    id = Integer(description=m.Device.id.comment, dump_only=True)
    hid = SanitizedStr(lower=True, dump_only=True, description=m.Device.hid.comment)
    tags = NestedOn('Tag',
                    many=True,
                    collection_class=OrderedSet,
                    description='The set of tags that identify the device.')
    model = SanitizedStr(lower=True, validate=Length(max=STR_BIG_SIZE))
    manufacturer = SanitizedStr(lower=True, validate=Length(max=STR_SIZE))
    serial_number = SanitizedStr(lower=True, data_key='serialNumber')
    weight = Float(validate=Range(0.1, 5), unit=UnitCodes.kgm, description=m.Device.weight.comment)
    width = Float(validate=Range(0.1, 5), unit=UnitCodes.m, description=m.Device.width.comment)
    height = Float(validate=Range(0.1, 5), unit=UnitCodes.m, description=m.Device.height.comment)
    depth = Float(validate=Range(0.1, 5), unit=UnitCodes.m, description=m.Device.depth.comment)
    events = NestedOn('Event', many=True, dump_only=True, description=m.Device.events.__doc__)
    events_one = NestedOn('Event', many=True, load_only=True, collection_class=OrderedSet)
    problems = NestedOn('Event', many=True, dump_only=True, description=m.Device.problems.__doc__)
    url = URL(dump_only=True, description=m.Device.url.__doc__)
    lots = NestedOn('Lot',
                    many=True,
                    dump_only=True,
                    description='The lots where this device is directly under.')
    rate = NestedOn('AggregateRate', dump_only=True, description=m.Device.rate.__doc__)
    price = NestedOn('Price', dump_only=True, description=m.Device.price.__doc__)
    trading = EnumField(states.Trading, dump_only=True, description=m.Device.trading.__doc__)
    physical = EnumField(states.Physical, dump_only=True, description=m.Device.physical.__doc__)
    physical_possessor = NestedOn('Agent', dump_only=True, data_key='physicalPossessor')
    production_date = DateTime('iso',
                               description=m.Device.updated.comment,
                               data_key='productionDate')
    working = NestedOn('Event',
                       many=True,
                       dump_only=True,
                       description=m.Device.working.__doc__)

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
    chassis = EnumField(enums.ComputerChassis, required=True)
    ram_size = Integer(dump_only=True, data_key='ramSize')
    data_storage_size = Integer(dump_only=True, data_key='dataStorageSize')
    processor_model = Str(dump_only=True, data_key='processorModel')
    graphic_card_model = Str(dump_only=True, data_key='graphicCardModel')
    network_speeds = List(Integer(dump_only=True), dump_only=True, data_key='networkSpeeds')
    privacy = NestedOn('Event', many=True, dump_only=True, collection_class=set)


class Desktop(Computer):
    pass


class Laptop(Computer):
    pass


class Server(Computer):
    pass


class DisplayMixin:
    size = Float(description=m.DisplayMixin.size.comment, validate=Range(2, 150))
    technology = EnumField(enums.DisplayTech,
                           description=m.DisplayMixin.technology.comment)
    resolution_width = Integer(data_key='resolutionWidth',
                               validate=Range(10, 20000),
                               description=m.DisplayMixin.resolution_width.comment)
    resolution_height = Integer(data_key='resolutionHeight',
                                validate=Range(10, 20000),
                                description=m.DisplayMixin.resolution_height.comment)
    refresh_rate = Integer(data_key='refreshRate', validate=Range(10, 1000))
    contrast_ratio = Integer(data_key='contrastRatio', validate=Range(100, 100000))
    touchable = Boolean(missing=False, description=m.DisplayMixin.touchable.comment)


class NetworkMixin:
    speed = Integer(validate=Range(min=10, max=10000),
                    unit=UnitCodes.mbps,
                    description=m.NetworkAdapter.speed.comment)
    wireless = Boolean(required=True)


class Monitor(DisplayMixin, Device):
    pass


class ComputerMonitor(Monitor):
    pass


class TelevisionSet(Monitor):
    pass


class Mobile(Device):
    imei = Integer(description=m.Mobile.imei.comment)
    meid = Str(description=m.Mobile.meid.comment)

    @pre_load
    def convert_check_imei(self, data):
        if data.get('imei', None):
            data['imei'] = int(imei.validate(data['imei']))
        return data

    @pre_load
    def convert_check_meid(self, data: dict):
        if data.get('meid', None):
            data['meid'] = meid.compact(data['meid'])
        return data


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
    interface = EnumField(enums.DataStorageInterface)
    privacy = NestedOn('Event', dump_only=True)


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
    cores = Integer(validate=Range(min=1, max=10))
    threads = Integer(validate=Range(min=1, max=20))
    address = Integer(validate=OneOf({8, 16, 32, 64, 128, 256}))


class RamModule(Component):
    size = Integer(validate=Range(min=128, max=17000), unit=UnitCodes.mbyte)
    speed = Integer(validate=Range(min=100, max=10000), unit=UnitCodes.mhz)
    interface = EnumField(enums.RamInterface)
    format = EnumField(enums.RamFormat)


class SoundCard(Component):
    pass


class Display(DisplayMixin, Component):
    pass


class Manufacturer(Schema):
    name = String(dump_only=True)
    url = URL(dump_only=True)
    logo = URL(dump_only=True)


class ComputerAccessory(Device):
    pass


class Mouse(ComputerAccessory):
    pass


class MemoryCardReader(ComputerAccessory):
    pass


class SAI(ComputerAccessory):
    pass


class Keyboard(ComputerAccessory):
    layout = EnumField(Layouts)


class Networking(NetworkMixin, Device):
    pass


class Router(Networking):
    pass


class Switch(Networking):
    pass


class Hub(Networking):
    pass


class WirelessAccessPoint(Networking):
    pass


class Printer(Device):
    wireless = Boolean(required=True, missing=False)
    scanning = Boolean(required=True, missing=False)
    technology = EnumField(enums.PrinterTechnology, required=True)
    monochrome = Boolean(required=True, missing=True)


class LabelPrinter(Printer):
    pass


class Sound(Device):
    pass


class Microphone(Sound):
    pass


class Video(Device):
    pass


class VideoScaler(Video):
    pass


class Videoconference(Video):
    pass


class Cooking(Device):
    pass


class Mixer(Cooking):
    pass
