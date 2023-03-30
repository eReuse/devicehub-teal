from typing import Callable, Iterable, Tuple

from ereuse_devicehub.resources.device import schemas
from ereuse_devicehub.resources.device.models import Manufacturer
from ereuse_devicehub.resources.device.views import (
    DeviceMergeView,
    DeviceView,
    ManufacturerView,
)
from ereuse_devicehub.teal.resource import Converters, Resource


class DeviceDef(Resource):
    SCHEMA = schemas.Device
    VIEW = DeviceView
    ID_CONVERTER = Converters.string
    AUTH = False  # We manage this at each view

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder='static',
        static_url_path=None,
        template_folder='templates',
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )

        device_merge = DeviceMergeView.as_view(
            'merge-devices', definition=self, auth=app.auth
        )

        if self.AUTH:
            device_merge = app.auth.requires_auth(device_merge)

        path = '/<{value}:dev1_id>/merge/<{value}:dev2_id>'.format(
            value=self.ID_CONVERTER.value
        )

        # self.add_url_rule(path, view_func=device_merge, methods={'POST'})


class ComputerDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Computer

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class DesktopDef(ComputerDef):
    VIEW = None
    SCHEMA = schemas.Desktop


class LaptopDef(ComputerDef):
    VIEW = None
    SCHEMA = schemas.Laptop


class ServerDef(ComputerDef):
    VIEW = None
    SCHEMA = schemas.Server


class MonitorDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Monitor

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class ComputerMonitorDef(MonitorDef):
    VIEW = None
    SCHEMA = schemas.ComputerMonitor


class TelevisionSetDef(MonitorDef):
    VIEW = None
    SCHEMA = schemas.TelevisionSet


class ProjectorDef(MonitorDef):
    VIEW = None
    SCHEMA = schemas.Projector


class MobileDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Mobile

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class SmartphoneDef(MobileDef):
    VIEW = None
    SCHEMA = schemas.Smartphone


class TabletDef(MobileDef):
    VIEW = None
    SCHEMA = schemas.Tablet


class CellphoneDef(MobileDef):
    VIEW = None
    SCHEMA = schemas.Cellphone


class ComponentDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Component

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class GraphicCardDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.GraphicCard


class DataStorageDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.DataStorage


class HardDriveDef(DataStorageDef):
    VIEW = None
    SCHEMA = schemas.HardDrive


class SolidStateDriveDef(DataStorageDef):
    VIEW = None
    SCHEMA = schemas.SolidStateDrive


class MotherboardDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.Motherboard


class NetworkAdapterDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.NetworkAdapter


class RamModuleDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.RamModule


class ProcessorDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.Processor


class SoundCardDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.SoundCard


class DisplayDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.Display


class BatteryDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.Battery


class CameraDef(ComponentDef):
    VIEW = None
    SCHEMA = schemas.Camera


class ComputerAccessoryDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.ComputerAccessory

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class MouseDef(ComputerAccessoryDef):
    VIEW = None
    SCHEMA = schemas.Mouse


class KeyboardDef(ComputerAccessoryDef):
    VIEW = None
    SCHEMA = schemas.Keyboard


class SAIDef(ComputerAccessoryDef):
    VIEW = None
    SCHEMA = schemas.SAI


class MemoryCardReaderDef(ComputerAccessoryDef):
    VIEW = None
    SCHEMA = schemas.MemoryCardReader


class NetworkingDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Networking

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class RouterDef(NetworkingDef):
    VIEW = None
    SCHEMA = schemas.Router


class SwitchDef(NetworkingDef):
    VIEW = None
    SCHEMA = schemas.Switch


class HubDef(NetworkingDef):
    VIEW = None
    SCHEMA = schemas.Hub


class WirelessAccessPointDef(NetworkingDef):
    VIEW = None
    SCHEMA = schemas.WirelessAccessPoint


class PrinterDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Printer

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class LabelPrinterDef(PrinterDef):
    VIEW = None
    SCHEMA = schemas.LabelPrinter


class SoundDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Sound

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class MicrophoneDef(SoundDef):
    VIEW = None
    SCHEMA = schemas.Microphone


class VideoDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Video

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class VideoScalerDef(VideoDef):
    VIEW = None
    SCHEMA = schemas.VideoScaler


class VideoconferenceDef(VideoDef):
    VIEW = None
    SCHEMA = schemas.Videoconference


class CookingDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Cooking

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class Mixer(CookingDef):
    VIEW = None
    SCHEMA = schemas.Mixer


class DIYAndGardeningDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.DIYAndGardening

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class DrillDef(DIYAndGardeningDef):
    VIEW = None
    SCHEMA = schemas.Drill


class PackOfScrewdriversDef(DIYAndGardeningDef):
    VIEW = None
    SCHEMA = schemas.PackOfScrewdrivers

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class HomeDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Home

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class DehumidifierDef(HomeDef):
    VIEW = None
    SCHEMA = schemas.Dehumidifier


class StairsDef(HomeDef):
    VIEW = None
    SCHEMA = schemas.Stairs


class RecreationDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Recreation

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )


class BikeDef(RecreationDef):
    VIEW = None
    SCHEMA = schemas.Bike


class RacketDef(RecreationDef):
    VIEW = None
    SCHEMA = schemas.Racket


class ManufacturerDef(Resource):
    VIEW = ManufacturerView
    SCHEMA = schemas.Manufacturer
    AUTH = True

    def init_db(self, db: 'db.SQLAlchemy', exclude_schema=None):
        """Loads the manufacturers to the database."""
        if exclude_schema != 'common':
            Manufacturer.add_all_to_session(db.session)


class OtherDef(DeviceDef):
    VIEW = None
    SCHEMA = schemas.Computer
    SCHEMA = schemas.Other

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )
