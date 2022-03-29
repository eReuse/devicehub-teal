import json
import logging
from enum import Enum, unique

from dmidecode import DMIParse

from ereuse_devicehub.parser.computer import Computer

logger = logging.getLogger(__name__)


class ParseSnapshot:
    def __init__(self, snapshot, default="n/a"):
        self.default = default
        self.dmidecode_raw = snapshot["data"]["dmidecode"]
        self.smart_raw = snapshot["data"]["smart"]
        self.hwinfo_raw = snapshot["data"]["hwinfo"]
        self.device = {"actions": []}
        self.components = []

        self.dmi = DMIParse(self.dmidecode_raw)
        self.smart = self.loads(self.smart_raw)
        self.hwinfo = self.parse_hwinfo()

        self.set_basic_datas()
        self.set_components()
        self.snapshot_json = {
            "device": self.device,
            "software": "Workbench",
            "components": self.components,
            "uuid": snapshot['uuid'],
            "type": snapshot['type'],
            "version": snapshot["version"],
            "endTime": snapshot["timestamp"],
            "elapsed": 1,
        }

    def set_basic_datas(self):
        self.device['manufacturer'] = self.dmi.manufacturer()
        self.device['model'] = self.dmi.model()
        self.device['serialNumber'] = self.dmi.serial_number()
        self.device['type'] = self.get_type()
        self.device['sku'] = self.get_sku()
        self.device['version'] = self.get_version()
        self.device['uuid'] = self.get_uuid()

    def set_components(self):
        self.get_cpu()
        self.get_ram()
        self.get_mother_board()
        self.get_data_storage()
        self.get_networks()

    def get_cpu(self):
        # TODO @cayop generation, brand and address not exist in dmidecode
        for cpu in self.dmi.get('Processor'):
            self.components.append(
                {
                    "actions": [],
                    "type": "Processor",
                    "speed": self.get_cpu_speed(cpu),
                    "cores": int(cpu.get('Core Count', 1)),
                    "model": cpu.get('Version'),
                    "threads": int(cpu.get('Thread Count', 1)),
                    "manufacturer": cpu.get('Manufacturer'),
                    "serialNumber": cpu.get('Serial Number'),
                    "generation": cpu.get('Generation'),
                    "brand": cpu.get('Brand'),
                    "address": cpu.get('Address'),
                }
            )

    def get_ram(self):
        # TODO @cayop format and model not exist in dmidecode
        for ram in self.dmi.get("Memory Device"):
            self.components.append(
                {
                    "actions": [],
                    "type": "RamModule",
                    "size": self.get_ram_size(ram),
                    "speed": self.get_ram_speed(ram),
                    "manufacturer": ram.get("Manufacturer", self.default),
                    "serialNumber": ram.get("Serial Number", self.default),
                    "interface": self.get_ram_type(ram),
                    "format": self.get_ram_format(ram),
                    "model": ram.get("Part Number", self.default),
                }
            )

    def get_mother_board(self):
        # TODO @cayop model, not exist in dmidecode
        for moder_board in self.dmi.get("Baseboard"):
            self.components.append(
                {
                    "actions": [],
                    "type": "Motherboard",
                    "version": moder_board.get("Version"),
                    "serialNumber": moder_board.get("Serial Number"),
                    "manufacturer": moder_board.get("Manufacturer"),
                    "biosDate": self.get_bios_date(),
                    # "firewire": self.get_firmware(),
                    "ramMaxSize": self.get_max_ram_size(),
                    "ramSlots": len(self.dmi.get("Memory Device")),
                    "slots": self.get_ram_slots(),
                    "model": moder_board.get("Product Name"),  # ??
                    "pcmcia": self.get_pcmcia_num(),  # ??
                    "serial": self.get_serial_num(),  # ??
                    "usb": self.get_usb_num(),
                }
            )

    def get_usb_num(self):
        return len(
            [u for u in self.dmi.get("Port Connector") if u.get("Port Type") == "USB"]
        )

    def get_serial_num(self):
        return len(
            [
                u
                for u in self.dmi.get("Port Connector")
                if u.get("Port Type") == "SERIAL"
            ]
        )

    def get_pcmcia_num(self):
        return len(
            [
                u
                for u in self.dmi.get("Port Connector")
                if u.get("Port Type") == "PCMCIA"
            ]
        )

    def get_bios_date(self):
        return self.dmi.get("BIOS")[0].get("Release Date", self.default)

    def get_firmware(self):
        return self.dmi.get("BIOS")[0].get("Firmware Revision", '1')

    def get_max_ram_size(self):
        size = 0
        for slot in self.dmi.get("Physical Memory Array"):
            capacity = slot.get("Maximum Capacity", '0').split(" ")[0]
            size += int(capacity)

        return size

    def get_ram_slots(self):
        slots = 0
        for x in self.dmi.get("Physical Memory Array"):
            slots += int(x.get("Number Of Devices", 0))
        return slots

    def get_ram_size(self, ram):
        size = ram.get("Size", "0")
        return int(size.split(" ")[0])

    def get_ram_speed(self, ram):
        size = ram.get("Speed", "0")
        return int(size.split(" ")[0])

    def get_ram_type(self, ram):
        TYPES = {'ddr', 'sdram', 'sodimm'}
        for t in TYPES:
            if t in ram.get("Type", "DDR"):
                return t

    def get_ram_format(self, ram):
        channel = ram.get("Locator", "DIMM")
        return 'SODIMM' if 'SODIMM' in channel else 'DIMM'

    def get_cpu_speed(self, cpu):
        speed = cpu.get('Max Speed', "0")
        return float(speed.split(" ")[0]) / 1024

    def get_sku(self):
        return self.dmi.get("System")[0].get("SKU Number", self.default)

    def get_version(self):
        return self.dmi.get("System")[0].get("Version", self.default)

    def get_uuid(self):
        return self.dmi.get("System")[0].get("UUID", self.default)

    def get_chassis(self):
        return self.dmi.get("Chassis")[0].get("Type", self.default)

    def get_type(self):
        chassis_type = self.get_chassis()
        return self.translation_to_devicehub(chassis_type)

    def translation_to_devicehub(self, original_type):
        lower_type = original_type.lower()
        CHASSIS_TYPE = {
            'Desktop': [
                'desktop',
                'low-profile',
                'tower',
                'docking',
                'all-in-one',
                'pizzabox',
                'mini-tower',
                'space-saving',
                'lunchbox',
                'mini',
                'stick',
            ],
            'Laptop': [
                'portable',
                'laptop',
                'convertible',
                'tablet',
                'detachable',
                'notebook',
                'handheld',
                'sub-notebook',
            ],
            'Server': ['server'],
            'Computer': ['_virtual'],
        }
        for k, v in CHASSIS_TYPE.items():
            if lower_type in v:
                return k
        return self.default

    def get_data_storage(self):

        for sm in self.smart:
            # import pdb; pdb.set_trace()
            model = sm.get('model_name')
            manufacturer = None
            if len(model.split(" ")) == 2:
                manufacturer, model = model.split(" ")

            self.components.append(
                {
                    "actions": [],
                    "type": self.get_data_storage_type(sm),
                    "model": model,
                    "manufacturer": manufacturer,
                    "serialNumber": sm.get('serial_number'),
                    "size": self.get_data_storage_size(sm),
                    "variant": sm.get("firmware_version"),
                    "interface": self.get_data_storage_interface(sm),
                }
            )

    def get_data_storage_type(self, x):
        # TODO @cayop add more SSDS types
        SSDS = ["nvme"]
        SSD = 'SolidStateDrive'
        HDD = 'HardDrive'
        type_dev = x.get('device', {}).get('type')
        return SSD if type_dev in SSDS else HDD

    def get_data_storage_interface(self, x):
        return x.get('device', {}).get('protocol', 'ATA')

    def get_data_storage_size(self, x):
        type_dev = x.get('device', {}).get('type')
        total_capacity = "{type}_total_capacity".format(type=type_dev)
        # convert bytes to Mb
        return x.get(total_capacity) / 1024**2

    def get_networks(self):
        hw_class = "  Hardware Class: "
        mac = "  Permanent HW Address: "
        model = "  Model: "
        wireless = "wireless"

        for line in self.hwinfo:
            iface = {
                "variant": "1",
                "actions": [],
                "speed": 100.0,
                "type": "NetworkAdapter",
                "wireless": False,
                "manufacturer": "Ethernet",
            }
            for y in line:
                if hw_class in y and not y.split(hw_class)[1] == 'network':
                    break

                if mac in y:
                    iface["serialNumber"] = y.split(mac)[1]
                if model in y:
                    iface["model"] = y.split(model)[1]
                if wireless in y:
                    iface["wireless"] = True

            if iface.get("serialNumber"):
                self.components.append(iface)

    def parse_hwinfo(self):
        hw_blocks = self.hwinfo_raw.split("\n\n")
        return [x.split("\n") for x in hw_blocks]

    def loads(self, x):
        if isinstance(x, str):
            return json.loads(x)
        return x


class ParseSnapshotLsHw:
    @unique
    class DataStorageInterface(Enum):
        ATA = 'ATA'
        USB = 'USB'
        PCI = 'PCI'
        NVME = 'NVME'

        def __str__(self):
            return self.value

    def __init__(self, snapshot, default="n/a"):
        self.default = default
        self.dmidecode_raw = snapshot["data"]["dmidecode"]
        self.smart_raw = snapshot["data"]["smart"]
        self.hwinfo_raw = snapshot["data"]["hwinfo"]
        self.lshw_raw = snapshot["data"]["lshw"]
        self.device = {"actions": []}
        self.components = []
        self.components_obj = []

        self.dmi = DMIParse(self.dmidecode_raw)
        self.smart = self.loads(self.smart_raw)
        self.hwinfo = self.parse_hwinfo()
        self.lshw = self.loads(self.lshw_raw)

        self.set_basic_datas()
        self.set_components()

        self.snapshot_json = {
            "device": self.device,
            "software": "Workbench",
            "components": self.components,
            "uuid": snapshot['uuid'],
            "type": snapshot['type'],
            "version": snapshot["version"],
            "endTime": snapshot["timestamp"],
            "elapsed": 1,
        }
        # import pdb; pdb.set_trace()

    def parse_hwinfo(self):
        hw_blocks = self.hwinfo_raw.split("\n\n")
        return [x.split("\n") for x in hw_blocks]

    def loads(self, x):
        if isinstance(x, str):
            return json.loads(x)
        return x

    def set_basic_datas(self):
        pc, self.components_obj = Computer.run(self.lshw_raw, self.hwinfo_raw)
        self.device = pc.dump()
        self.device['uuid'] = self.dmi.get("System")[0].get("UUID")

    def set_components(self):
        memory = None

        for x in self.components_obj:
            if x.type == 'RamModule':
                memory = 1

            if x.type == 'Motherboard':
                x.slots = self.get_ram_slots()

            self.components.append(x.dump())

        if not memory:
            self.get_ram()

        self.get_data_storage()

    def get_ram(self):
        for ram in self.dmi.get("Memory Device"):
            self.components.append(
                {
                    "actions": [],
                    "type": "RamModule",
                    "size": self.get_ram_size(ram),
                    "speed": self.get_ram_speed(ram),
                    "manufacturer": ram.get("Manufacturer", self.default),
                    "serialNumber": ram.get("Serial Number", self.default),
                    "interface": self.get_ram_type(ram),
                    "format": self.get_ram_format(ram),
                    "model": ram.get("Part Number", self.default),
                }
            )

    def get_ram_size(self, ram):
        size = ram.get("Size", "0")
        return int(size.split(" ")[0])

    def get_ram_speed(self, ram):
        size = ram.get("Speed", "0")
        return int(size.split(" ")[0])

    def get_ram_slots(self):
        slots = 0
        for x in self.dmi.get("Physical Memory Array"):
            slots += int(x.get("Number Of Devices", 0))
        return slots

    def get_ram_type(self, ram):
        TYPES = {'ddr', 'sdram', 'sodimm'}
        for t in TYPES:
            if t in ram.get("Type", "DDR"):
                return t

    def get_ram_format(self, ram):
        channel = ram.get("Locator", "DIMM")
        return 'SODIMM' if 'SODIMM' in channel else 'DIMM'

    def get_data_storage(self):

        for sm in self.smart:
            # import pdb; pdb.set_trace()
            model = sm.get('model_name')
            manufacturer = None
            if len(model.split(" ")) > 1:
                mm = model.split(" ")
                model = mm[-1]
                manufacturer = " ".join(mm[:-1])

            self.components.append(
                {
                    "actions": [self.get_test_data_storage(sm)],
                    "type": self.get_data_storage_type(sm),
                    "model": model,
                    "manufacturer": manufacturer,
                    "serialNumber": sm.get('serial_number'),
                    "size": self.get_data_storage_size(sm),
                    "variant": sm.get("firmware_version"),
                    "interface": self.get_data_storage_interface(sm),
                }
            )

    def get_data_storage_type(self, x):
        # TODO @cayop add more SSDS types
        SSDS = ["nvme"]
        SSD = 'SolidStateDrive'
        HDD = 'HardDrive'
        type_dev = x.get('device', {}).get('type')
        return SSD if type_dev in SSDS else HDD

    def get_data_storage_interface(self, x):
        interface = x.get('device', {}).get('protocol', 'ATA')
        try:
            self.DataStorageInterface(interface.upper())
        except ValueError as err:
            logger.error(
                "interface {} is not in DataStorageInterface Enum".format(interface)
            )
            raise err

    def get_data_storage_size(self, x):
        type_dev = x.get('device', {}).get('type')
        total_capacity = "{type}_total_capacity".format(type=type_dev)
        # convert bytes to Mb
        return x.get(total_capacity) / 1024**2

    def get_test_data_storage(self, smart):
        log = "smart_health_information_log"
        action = {
            "status": "Completed without error",
            "reallocatedSectorCount": smart.get("reallocated_sector_count", 0),
            "currentPendingSectorCount": smart.get("current_pending_sector_count", 0),
            "assessment": True,
            "severity": "Info",
            "offlineUncorrectable": smart.get("offline_uncorrectable", 0),
            "lifetime": 0,
            "type": "TestDataStorage",
            "length": "Short",
            "elapsed": 0,
            "reportedUncorrectableErrors": smart.get(
                "reported_uncorrectable_errors", 0
            ),
            "powerCycleCount": smart.get("power_cycle_count", 0),
        }

        for k in smart.keys():
            if log in k:
                action['lifetime'] = smart[k].get("power_on_hours", 0)
                action['powerOnHours'] = smart[k].get("power_on_hours", 0)

        return action
