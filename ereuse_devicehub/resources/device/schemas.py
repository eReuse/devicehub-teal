import datetime

from marshmallow import fields as f
from marshmallow import post_load, pre_load
from marshmallow.fields import (
    UUID,
    Boolean,
    Date,
    DateTime,
    Dict,
    Float,
    Integer,
    List,
    Str,
    String,
)
from marshmallow.validate import Length, OneOf, Range
from sqlalchemy.util import OrderedSet
from stdnum import meid

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources import enums
from ereuse_devicehub.resources.device import models as m
from ereuse_devicehub.resources.device import states
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing, UnitCodes
from ereuse_devicehub.teal.enums import Layouts
from ereuse_devicehub.teal.marshmallow import (
    URL,
    EnumField,
    SanitizedStr,
    ValidationError,
)
from ereuse_devicehub.teal.resource import Schema


class Device(Thing):
    __doc__ = m.Device.__doc__
    id = Integer(description=m.Device.id.comment, dump_only=True)
    hid = SanitizedStr(lower=True, description=m.Device.hid.comment)
    tags = NestedOn(
        'Tag',
        many=True,
        collection_class=OrderedSet,
        description='A set of tags that identify the device.',
    )
    model = SanitizedStr(
        lower=True,
        validate=Length(max=STR_BIG_SIZE),
        description=m.Device.model.comment,
    )
    manufacturer = SanitizedStr(
        lower=True,
        validate=Length(max=STR_SIZE),
        description=m.Device.manufacturer.comment,
    )
    serial_number = SanitizedStr(
        lower=True, validate=Length(max=STR_BIG_SIZE), data_key='serialNumber'
    )
    part_number = SanitizedStr(
        lower=True, validate=Length(max=STR_BIG_SIZE), data_key='partNumber'
    )
    brand = SanitizedStr(
        validate=Length(max=STR_BIG_SIZE), description=m.Device.brand.comment
    )
    generation = Integer(
        validate=Range(1, 100), description=m.Device.generation.comment
    )
    version = SanitizedStr(description=m.Device.version)
    weight = Float(
        validate=Range(0.1, 5), unit=UnitCodes.kgm, description=m.Device.weight.comment
    )
    width = Float(
        validate=Range(0.1, 5), unit=UnitCodes.m, description=m.Device.width.comment
    )
    height = Float(
        validate=Range(0.1, 5), unit=UnitCodes.m, description=m.Device.height.comment
    )
    depth = Float(
        validate=Range(0.1, 5), unit=UnitCodes.m, description=m.Device.depth.comment
    )
    # TODO TimeOut 2. Comment actions and lots if there are time out.
    actions = NestedOn(
        'Action', many=True, dump_only=True, description=m.Device.actions.__doc__
    )
    # TODO TimeOut 2. Comment actions_one and lots if there are time out.
    actions_one = NestedOn(
        'Action', many=True, load_only=True, collection_class=OrderedSet
    )
    problems = NestedOn(
        'Action', many=True, dump_only=True, description=m.Device.problems.__doc__
    )
    url = URL(dump_only=True, description=m.Device.url.__doc__)
    # TODO TimeOut 2. Comment actions and lots if there are time out.
    lots = NestedOn(
        'Lot',
        many=True,
        dump_only=True,
        description='The lots where this device is directly under.',
    )
    rate = NestedOn('Rate', dump_only=True, description=m.Device.rate.__doc__)
    price = NestedOn('Price', dump_only=True, description=m.Device.price.__doc__)
    tradings = Dict(dump_only=True, description='')
    physical = EnumField(
        states.Physical, dump_only=True, description=m.Device.physical.__doc__
    )
    traking = EnumField(
        states.Traking, dump_only=True, description=m.Device.physical.__doc__
    )
    usage = EnumField(
        states.Usage, dump_only=True, description=m.Device.physical.__doc__
    )
    revoke = UUID(dump_only=True)
    physical_possessor = NestedOn('Agent', dump_only=True, data_key='physicalPossessor')
    production_date = DateTime(
        'iso', description=m.Device.updated.comment, data_key='productionDate'
    )
    working = NestedOn(
        'Action', many=True, dump_only=True, description=m.Device.working.__doc__
    )
    variant = SanitizedStr(description=m.Device.variant.comment)
    sku = SanitizedStr(description=m.Device.sku.comment)
    image = URL(description=m.Device.image.comment)
    allocated = Boolean(description=m.Device.allocated.comment)
    dhid = SanitizedStr(
        data_key='devicehubID', description=m.Device.devicehub_id.comment
    )
    family = SanitizedStr(validate=Length(max=STR_BIG_SIZE))

    @pre_load
    def from_actions_to_actions_one(self, data: dict):
        """
        Not an elegant way of allowing submitting actions to a device
        (in the context of Snapshots) without creating an ``actions``
        field at the model (which is not possible).
        :param data:
        :return:
        """
        # Note that it is secure to allow uploading actions_one
        # as the only time an user can send a device object is
        # in snapshots.
        data['actions_one'] = data.pop('actions', [])
        return data

    @post_load
    def validate_snapshot_actions(self, data):
        """Validates that only snapshot-related actions can be uploaded."""
        from ereuse_devicehub.resources.action.models import (
            Benchmark,
            EraseBasic,
            Install,
            Rate,
            Test,
        )

        for action in data['actions_one']:
            if not isinstance(action, (Install, EraseBasic, Rate, Test, Benchmark)):
                raise ValidationError(
                    'You cannot upload {}'.format(action), field_names=['actions']
                )


class Computer(Device):
    __doc__ = m.Computer.__doc__
    # TODO TimeOut 1. Comment components if there are time out.
    components = NestedOn(
        'Component',
        many=True,
        dump_only=True,
        collection_class=OrderedSet,
        description='The components that are inside this computer.',
    )
    chassis = EnumField(enums.ComputerChassis, description=m.Computer.chassis.comment)
    ram_size = Integer(
        dump_only=True, data_key='ramSize', description=m.Computer.ram_size.__doc__
    )
    data_storage_size = Integer(
        dump_only=True,
        data_key='dataStorageSize',
        description=m.Computer.data_storage_size.__doc__,
    )
    processor_model = Str(
        dump_only=True,
        data_key='processorModel',
        description=m.Computer.processor_model.__doc__,
    )
    graphic_card_model = Str(
        dump_only=True,
        data_key='graphicCardModel',
        description=m.Computer.graphic_card_model.__doc__,
    )
    network_speeds = List(
        Integer(dump_only=True),
        dump_only=True,
        data_key='networkSpeeds',
        description=m.Computer.network_speeds.__doc__,
    )
    privacy = NestedOn(
        'Action',
        many=True,
        dump_only=True,
        collection_class=set,
        description=m.Computer.privacy.__doc__,
    )
    amount = Integer(
        validate=f.validate.Range(min=0, max=100), description=m.Computer.amount.__doc__
    )
    # author_id = NestedOn(s_user.User, only_query='author_id')
    owner_id = UUID(data_key='ownerID')
    transfer_state = EnumField(
        enums.TransferState, description=m.Computer.transfer_state.comment
    )
    receiver_id = UUID(data_key='receiverID')
    system_uuid = UUID(required=False)


class Desktop(Computer):
    __doc__ = m.Desktop.__doc__


class Laptop(Computer):
    __doc__ = m.Laptop.__doc__
    layout = EnumField(Layouts, description=m.Laptop.layout.comment)


class Server(Computer):
    __doc__ = m.Server.__doc__


class DisplayMixin:
    __doc__ = m.DisplayMixin.__doc__
    size = Float(description=m.DisplayMixin.size.comment, validate=Range(2, 150))
    technology = EnumField(
        enums.DisplayTech, description=m.DisplayMixin.technology.comment
    )
    resolution_width = Integer(
        data_key='resolutionWidth',
        validate=Range(10, 20000),
        description=m.DisplayMixin.resolution_width.comment,
    )
    resolution_height = Integer(
        data_key='resolutionHeight',
        validate=Range(10, 20000),
        description=m.DisplayMixin.resolution_height.comment,
    )
    refresh_rate = Integer(data_key='refreshRate', validate=Range(10, 1000))
    contrast_ratio = Integer(data_key='contrastRatio', validate=Range(100, 100000))
    touchable = Boolean(description=m.DisplayMixin.touchable.comment)
    aspect_ratio = String(
        dump_only=True, description=m.DisplayMixin.aspect_ratio.__doc__
    )
    widescreen = Boolean(dump_only=True, description=m.DisplayMixin.widescreen.__doc__)


class NetworkMixin:
    __doc__ = m.NetworkMixin.__doc__

    speed = Integer(
        validate=Range(min=10, max=10000),
        unit=UnitCodes.mbps,
        description=m.NetworkAdapter.speed.comment,
    )
    wireless = Boolean(required=True)


class Monitor(DisplayMixin, Device):
    __doc__ = m.Monitor.__doc__


class ComputerMonitor(Monitor):
    __doc__ = m.ComputerMonitor.__doc__


class TelevisionSet(Monitor):
    __doc__ = m.TelevisionSet.__doc__


class Projector(Monitor):
    __doc__ = m.Projector.__doc__


class Mobile(Device):
    __doc__ = m.Mobile.__doc__

    imei = Integer(description=m.Mobile.imei.comment)
    meid = Str(description=m.Mobile.meid.comment)
    ram_size = Integer(
        validate=Range(min=128, max=36000),
        data_key='ramSize',
        unit=UnitCodes.mbyte,
        description=m.Mobile.ram_size.comment,
    )
    data_storage_size = Integer(
        validate=Range(0, 10**8),
        data_key='dataStorageSize',
        description=m.Mobile.data_storage_size,
    )
    display_size = Float(
        validate=Range(min=0.1, max=30.0),
        data_key='displaySize',
        description=m.Mobile.display_size.comment,
    )

    @pre_load
    def convert_check_imei(self, data):
        if data.get('imei', None):
            # data['imei'] = int(imei.validate(data['imei']))
            data['imei'] = int(data['imei'].replace("-", ""))
        return data

    @pre_load
    def convert_check_meid(self, data: dict):
        if data.get('meid', None):
            data['meid'] = meid.compact(data['meid'])
        return data


class Smartphone(Mobile):
    __doc__ = m.Smartphone.__doc__


class Tablet(Mobile):
    __doc__ = m.Tablet.__doc__


class Cellphone(Mobile):
    __doc__ = m.Cellphone.__doc__


class Component(Device):
    __doc__ = m.Component.__doc__

    parent = NestedOn(Device, dump_only=True)


class GraphicCard(Component):
    __doc__ = m.GraphicCard.__doc__

    memory = Integer(
        validate=Range(0, 10000),
        unit=UnitCodes.mbyte,
        description=m.GraphicCard.memory.comment,
    )


class DataStorage(Component):
    __doc__ = m.DataStorage.__doc__

    size = Integer(
        validate=Range(0, 10**8),
        unit=UnitCodes.mbyte,
        description=m.DataStorage.size.comment,
    )
    interface = EnumField(enums.DataStorageInterface)
    privacy = NestedOn('Action', dump_only=True)


class HardDrive(DataStorage):
    __doc__ = m.HardDrive.__doc__


class SolidStateDrive(DataStorage):
    __doc__ = m.SolidStateDrive.__doc__


class Motherboard(Component):
    __doc__ = m.Motherboard.__doc__

    slots = Integer(validate=Range(0, 20), description=m.Motherboard.slots.comment)
    usb = Integer(validate=Range(0, 20), description=m.Motherboard.usb.comment)
    firewire = Integer(
        validate=Range(0, 20), description=m.Motherboard.firewire.comment
    )
    serial = Integer(validate=Range(0, 20), description=m.Motherboard.serial.comment)
    pcmcia = Integer(validate=Range(0, 20), description=m.Motherboard.pcmcia.comment)
    bios_date = Date(
        validate=Range(
            datetime.date(year=1980, month=1, day=1),
            datetime.date(year=2030, month=1, day=1),
        ),
        data_key='biosDate',
        description=m.Motherboard.bios_date,
    )
    ram_slots = Integer(validate=Range(1), data_key='ramSlots')
    ram_max_size = Integer(validate=Range(1), data_key='ramMaxSize')


class NetworkAdapter(NetworkMixin, Component):
    __doc__ = m.NetworkAdapter.__doc__


class Processor(Component):
    __doc__ = m.Processor.__doc__

    speed = Float(
        validate=Range(min=0.1, max=15),
        unit=UnitCodes.ghz,
        description=m.Processor.speed.comment,
    )
    cores = Integer(
        validate=Range(min=1, max=10), description=m.Processor.cores.comment
    )
    threads = Integer(
        validate=Range(min=1, max=20), description=m.Processor.threads.comment
    )
    address = Integer(
        validate=OneOf({8, 16, 32, 64, 128, 256}),
        description=m.Processor.address.comment,
    )
    abi = SanitizedStr(lower=True, description=m.Processor.abi.comment)


class RamModule(Component):
    __doc__ = m.RamModule.__doc__

    size = Integer(
        validate=Range(min=128, max=17000),
        unit=UnitCodes.mbyte,
        description=m.RamModule.size.comment,
    )
    speed = Integer(validate=Range(min=100, max=10000), unit=UnitCodes.mhz)
    interface = EnumField(enums.RamInterface)
    format = EnumField(enums.RamFormat)


class SoundCard(Component):
    __doc__ = m.SoundCard.__doc__


class Display(DisplayMixin, Component):
    __doc__ = m.Display.__doc__


class Battery(Component):
    __doc__ = m.Battery.__doc__

    wireless = Boolean(description=m.Battery.wireless.comment)
    technology = EnumField(
        enums.BatteryTechnology, description=m.Battery.technology.comment
    )
    size = Integer(required=True, description=m.Battery.size.comment)


class Camera(Component):
    __doc__ = m.Camera.__doc__

    focal_length = Integer(data_key='focalLength')
    video_height = Integer(data_key='videoHeight')
    video_width = Integer(data_key='videoWidth')
    horizontal_view_angle = Integer(data_key='horizontalViewAngle')
    facing = Integer()
    vertical_view_angle = Integer(data_key='verticalViewAngle')
    video_stabilization = Integer(data_key='videoStabilization')
    flash = Integer()


class Manufacturer(Schema):
    __doc__ = m.Manufacturer.__doc__

    name = String(dump_only=True)
    url = URL(dump_only=True)
    logo = URL(dump_only=True)


class ComputerAccessory(Device):
    __doc__ = m.ComputerAccessory.__doc__


class Mouse(ComputerAccessory):
    __doc__ = m.Mouse.__doc__


class MemoryCardReader(ComputerAccessory):
    __doc__ = m.MemoryCardReader.__doc__


class SAI(ComputerAccessory):
    __doc__ = m.SAI.__doc__


class Keyboard(ComputerAccessory):
    __doc__ = m.Keyboard.__doc__

    layout = EnumField(Layouts)


class Networking(NetworkMixin, Device):
    __doc__ = m.Networking.__doc__


class Router(Networking):
    __doc__ = m.Router.__doc__


class Switch(Networking):
    __doc__ = m.Switch.__doc__


class Hub(Networking):
    __doc__ = m.Hub.__doc__


class WirelessAccessPoint(Networking):
    __doc__ = m.WirelessAccessPoint.__doc__


class Printer(Device):
    __doc__ = m.Printer.__doc__

    wireless = Boolean(
        required=True, missing=False, description=m.Printer.wireless.comment
    )
    scanning = Boolean(
        required=True, missing=False, description=m.Printer.scanning.comment
    )
    technology = EnumField(
        enums.PrinterTechnology, required=True, description=m.Printer.technology.comment
    )
    monochrome = Boolean(
        required=True, missing=True, description=m.Printer.monochrome.comment
    )


class LabelPrinter(Printer):
    __doc__ = m.LabelPrinter.__doc__


class Sound(Device):
    __doc__ = m.Sound.__doc__


class Microphone(Sound):
    __doc__ = m.Microphone.__doc__


class Video(Device):
    __doc__ = m.Video.__doc__


class VideoScaler(Video):
    __doc__ = m.VideoScaler.__doc__


class Videoconference(Video):
    __doc__ = m.Videoconference.__doc__


class Cooking(Device):
    __doc__ = m.Cooking.__doc__


class Mixer(Cooking):
    __doc__ = m.Mixer.__doc__


class DIYAndGardening(Device):
    pass


class Drill(DIYAndGardening):
    max_drill_bit_size = Integer(data_key='maxDrillBitSize')


class PackOfScrewdrivers(DIYAndGardening):
    size = Integer()


class Home(Device):
    pass


class Dehumidifier(Home):
    size = Integer()


class Stairs(Home):
    max_allowed_weight = Integer(data_key='maxAllowedWeight')


class Recreation(Device):
    pass


class Bike(Recreation):
    wheel_size = Integer(data_key='wheelSize')
    gears = Integer()


class Racket(Recreation):
    pass


class Other(Device):
    pass
