import json

from dmidecode import DMIParse

from ereuse_devicehub.parser.computer import (
    Display,
    GraphicCard,
    NetworkAdapter,
    SoundCard,
)


class ParseSnapshot:
    def __init__(self, snapshot, default="n/a"):
        self.default = default
        self.dmidecode_raw = snapshot["data"]["demidecode"]
        self.smart_raw = snapshot["data"]["smart"]
        self.hwinfo_raw = snapshot["data"]["hwinfo"]
        self.device = {"actions": []}
        self.components = []

        self.dmi = DMIParse(self.dmidecode_raw)
        self.smart = self.loads(self.smart_raw)
        self.hwinfo = self.parse_hwinfo()

        self.set_basic_datas()
        self.computer = {
            "device": self.device,
            "software": "Workbench",
            "components": self.components(),
            "uuid": snapshot['uuid'],
            "type": snapshot['type'],
            "version": snapshot["version"],
            "endTime": snapshot["endTime"],
            "elapsed": 0,
            "closed": True,
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

    def get_cpu(self):
        # TODO @cayop generation, brand and address not exist in dmidecode
        for cpu in self.dmi.get('Processor'):
            self.components.append(
                {
                    "actions": [],
                    "type": "Processor",
                    "speed": cpu.get('Max Speed'),
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
                    "interface": ram.get("Type", self.default),
                    "format": ram.get("Format", self.default),  # "DIMM",
                    "model": ram.get(
                        "Model", self.default
                    ),  # "48594D503131325336344350362D53362020",
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
                    "ramSlots": self.get_ram_slots(),
                    "ramMaxSize": self.get_max_ram_size(),
                    "slots": len(self.dmi.get("Number Of Devices")),
                    "biosDate": self.get_bios_date(),
                    "firewire": self.get_firmware(),
                    "model": moder_board.get("Product Name"),  # ??
                    "pcmcia": self.get_pcmcia_num(),  # ??
                    "serial": self.get_serial_num(),  # ??
                    "usb": self.get_usb_num(),
                }
            )

    def get_usb_num(self):
        return len(
            [u for u in self.get("Port Connector") if u.get("Port Type") == "USB"]
        )

    def get_serial_num(self):
        return len(
            [u for u in self.get("Port Connector") if u.get("Port Type") == "SERIAL"]
        )

    def get_pcmcia_num(self):
        return len(
            [u for u in self.get("Port Connector") if u.get("Port Type") == "PCMCIA"]
        )

    def get_bios_date(self):
        return self.get("BIOS")[0].get("Release Date", self.default)

    def get_firmware(self):
        return self.get("BIOS")[0].get("Firmware Revision", self.default)

    def get_max_ram_size(self):
        size = self.dmi.get("Physical Memory Array")
        if size:
            size = size.get("Maximum Capacity")

        return size.split(" GB")[0] if size else self.default

    def get_ram_slots(self):
        slots = self.dmi.get("Physical Memory Array")
        if slots:
            slots = slots.get("Number Of Devices")
        return int(slots) if slots else self.default

    def get_ram_size(self, ram):
        size = ram.get("Size")
        return size.split(" MB")[0] if size else self.default

    def get_ram_speed(self, ram):
        size = ram.get("Speed")
        return size.split(" MT/s")[0] if size else self.default

    def get_sku(self):
        return self.get("System")[0].get("SKU Number", self.default)

    def get_version(self):
        return self.get("System")[0].get("Version", self.default)

    def get_uuid(self):
        return self.get("System")[0].get("UUID", self.default)

    def get_chassis(self):
        return self.get("Chassis")[0].get("Type", self.default)

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
        addr = []
        for line in self.hwinfo:
            for y in line:
                if "Permanent HW Address:" in y:
                    mac = y.split("  Permanent HW Address: ")[1]
                    addr.extend(mac)

        return addr

    def parse_hwinfo(self):
        hw_blocks = self.hwinfo_raw.split("\n\n")
        return [x.split("\n") for x in hw_blocks]

    def loads(self, x):
        if isinstance(x, dict) or isinstance(x, list):
            return x
        return json.loads(x)


class LsHw:
    def __init__(self, dmi, jshw, hwinfo, default="n/a"):
        self.default = default
        self.hw = self.loads(jshw)
        self.hwinfo = hwinfo.splitlines()
        self.childrens = self.hw.get('children', [])
        self.dmi = dmi
        self.components = dmi.components
        self.device = dmi.device
        self.add_components()

    def add_components(self):
        self.get_cpu_addr()
        self.get_networks()
        self.get_display()
        self.get_sound_card()
        self.get_graphic_card()

    def get_cpu_addr(self):
        for cpu in self.components:
            if not cpu['type'] == "Processor":
                continue

            cpu["address"] = self.hw.get("width")

    def get_networks(self):
        networks = NetworkAdapter.new(self.lshw, self.hwinfo)

        for x in networks:
            self.components.append(
                {
                    "actions": [],
                    "type": "NetworkAdapter",
                    "serialNumber": x.serial_number,
                    "speed": x.speed,
                    "model": x.model,
                    "manufacturer": x.manufacturer,
                    "variant": x.variant,
                    "wireless": x.wireless,
                }
            )

    def get_display(self):
        if not self.device['type'] == 'Laptop':
            return

        displays = Display.new(self.lshw, self.hwinfo)

        for x in displays:
            self.components.append(
                {
                    "actions": [],
                    "type": "Display",
                    "model": x.model,
                    "manufacturer": x.manufacturer,
                    "serialNumber": x.serial_number,
                    "resolutionWidth": x.resolution_width,
                    "resolutionHeight": x.resolution_height,
                    "refreshRate": x.refresh_rate,
                    "technology": x.technology,
                    "productionDate": x.production_date,
                    "size": x.size,
                }
            )

    def get_sound_card(self):
        soundcards = SoundCard.new(self.lshw, self.hwinfo)

        for x in soundcards:
            self.components.append(
                {
                    "actions": [],
                    "type": "SoundCard",
                    "model": x.model,
                    "manufacturer": x.manufacturer,
                    "serialNumber": x.serial_number,
                }
            )

    def get_graphic_card(self):
        # TODO @cayop memory get info from lspci on fly
        graphicards = GraphicCard.new(self.lshw, self.hwinfo)

        for x in graphicards:
            self.components.append(
                {
                    "actions": [],
                    "type": "GraphicCard",
                    "model": x.model,
                    "manufacturer": x.manufacturer,
                    "serialNumber": x.serial_number,
                    "memory": x.memory,
                }
            )

    def loads(jshw):
        if isinstance(jshw, dict):
            return jshw
        return json.loads(jshw)
