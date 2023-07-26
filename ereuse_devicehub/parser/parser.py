import json
import logging
import uuid
from datetime import datetime

import numpy
from dmidecode import DMIParse
from flask import request
from marshmallow.exceptions import ValidationError

from ereuse_devicehub.ereuse_utils.nested_lookup import get_nested_dicts_with_key_value
from ereuse_devicehub.parser import base2, unit
from ereuse_devicehub.parser.computer import Computer
from ereuse_devicehub.parser.models import SnapshotsLog
from ereuse_devicehub.resources.action.schemas import Snapshot
from ereuse_devicehub.resources.enums import DataStorageInterface, Severity

logger = logging.getLogger(__name__)


class ParseSnapshot:
    def __init__(self, snapshot, default="n/a"):
        self.default = default
        self.dmidecode_raw = snapshot["hwmd"]["dmidecode"]
        self.smart_raw = snapshot["hwmd"]["smart"]
        self.hwinfo_raw = snapshot["hwmd"]["hwinfo"]
        self.lshw_raw = snapshot["hwmd"]["lshw"]
        self.lscpi_raw = snapshot["hwmd"]["lspci"]
        self.sanitize_raw = snapshot.get("sanitize", [])
        self.device = {"actions": []}
        self.components = []
        self.monitors = []

        self.dmi = DMIParse(self.dmidecode_raw)
        self.smart = self.loads(self.smart_raw)
        self.lshw = self.loads(self.lshw_raw)
        self.hwinfo = self.parse_hwinfo()

        self.set_computer()
        self.get_hwinfo_monitors()
        self.set_components()
        self.snapshot_json = {
            "device": self.device,
            "software": "UsodyOS",
            "components": self.components,
            "uuid": snapshot['uuid'],
            "version": snapshot['version'],
            "settings_version": snapshot['settings_version'],
            "endTime": snapshot["timestamp"],
            "elapsed": 1,
            "sid": snapshot["sid"],
        }

    def get_snapshot(self):
        return Snapshot().load(self.snapshot_json)

    def set_computer(self):
        self.device['manufacturer'] = self.dmi.manufacturer()
        self.device['model'] = self.dmi.model()
        self.device['serialNumber'] = self.dmi.serial_number()
        self.device['type'] = self.get_type()
        self.device['sku'] = self.get_sku()
        self.device['version'] = self.get_version()
        self.device['system_uuid'] = self.get_uuid()
        self.device['family'] = self.get_family()
        self.device['chassis'] = self.get_chassis_dh()

    def set_components(self):
        self.get_cpu()
        self.get_ram()
        self.get_mother_board()
        self.get_graphic()
        self.get_data_storage()
        self.get_display()
        self.get_sound_card()
        self.get_networks()

    def get_cpu(self):
        for cpu in self.dmi.get('Processor'):
            serial = cpu.get('Serial Number')
            if serial == 'Not Specified' or not serial:
                serial = cpu.get('ID').replace(' ', '')
            self.components.append(
                {
                    "actions": [],
                    "type": "Processor",
                    "speed": self.get_cpu_speed(cpu),
                    "cores": int(cpu.get('Core Count', 1)),
                    "model": cpu.get('Version'),
                    "threads": int(cpu.get('Thread Count', 1)),
                    "manufacturer": cpu.get('Manufacturer'),
                    "serialNumber": serial,
                    "generation": None,
                    "brand": cpu.get('Family'),
                    "address": self.get_cpu_address(cpu),
                }
            )

    def get_ram(self):
        for ram in self.dmi.get("Memory Device"):
            if ram.get('size') == 'No Module Installed':
                continue
            if not ram.get("Speed"):
                continue

            self.components.append(
                {
                    "actions": [],
                    "type": "RamModule",
                    "size": self.get_ram_size(ram),
                    "speed": self.get_ram_speed(ram),
                    "manufacturer": ram.get("Manufacturer", self.default),
                    "serialNumber": ram.get("Serial Number", self.default),
                    "interface": ram.get("Type", "DDR"),
                    "format": ram.get("Form Factor", "DIMM"),
                    "model": ram.get("Part Number", self.default),
                }
            )

    def get_mother_board(self):
        for moder_board in self.dmi.get("Baseboard"):
            self.components.append(
                {
                    "actions": [],
                    "type": "Motherboard",
                    "version": moder_board.get("Version"),
                    "serialNumber": moder_board.get("Serial Number"),
                    "manufacturer": moder_board.get("Manufacturer"),
                    "biosDate": self.get_bios_date(),
                    "ramMaxSize": self.get_max_ram_size(),
                    "ramSlots": len(self.dmi.get("Memory Device")),
                    "slots": self.get_ram_slots(),
                    "model": moder_board.get("Product Name"),
                    "firewire": self.get_firmware_num(),
                    "pcmcia": self.get_pcmcia_num(),
                    "serial": self.get_serial_num(),
                    "usb": self.get_usb_num(),
                }
            )

    def get_graphic(self):
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'display')
        for c in nodes:
            if not c['configuration'].get('driver', None):
                continue

            self.components.append(
                {
                    "actions": [],
                    "type": "GraphicCard",
                    "memory": self.get_memory_video(c),
                    "manufacturer": c.get("vendor", self.default),
                    "model": c.get("product", self.default),
                    "serialNumber": c.get("serial", self.default),
                }
            )

    def get_memory_video(self, c):
        # get info of lspci
        # pci_id = c['businfo'].split('@')[1]
        # lspci.get(pci_id) | grep size
        # lspci -v -s 00:02.0
        return None

    def get_data_storage(self):
        for sm in self.smart:
            if sm.get('smartctl', {}).get('exit_status') == 1:
                continue
            model = sm.get('model_name')
            manufacturer = None
            if model and len(model.split(" ")) > 1:
                mm = model.split(" ")
                model = mm[-1]
                manufacturer = " ".join(mm[:-1])

            self.components.append(
                {
                    "actions": self.sanitize(sm),
                    "type": self.get_data_storage_type(sm),
                    "model": model,
                    "manufacturer": manufacturer,
                    "serialNumber": sm.get('serial_number'),
                    "size": self.get_data_storage_size(sm),
                    "variant": sm.get("firmware_version"),
                    "interface": self.get_data_storage_interface(sm),
                }
            )

    def sanitize(self, disk):
        disk_sanitize = None
        # import pdb; pdb.set_trace()
        for d in self.sanitize_raw:
            s = d.get('device_info', {}).get('export_data', {})
            s = s.get('block', {}).get('serial')
            if s == disk.get('serial_number'):
                disk_sanitize = d
                break
        if not disk_sanitize:
            return []

        steps = []
        step_type = 'EraseBasic'
        if disk.get('name') == 'Baseline Cryptographic':
            step_type = 'EraseCrypto'

        if disk.get('type') == 'EraseCrypto':
            step_type = 'EraseCrypto'

        erase = {
            'type': step_type,
            'severity': disk_sanitize['severity'].name,
            'steps': steps,
            'startTime': None,
            'endTime': None,
        }

        for step in disk_sanitize.get('steps', []):
            steps.append(
                {
                    'severity': step['severity'].name,
                    'startTime': step['start_time'].isoformat(),
                    'endTime': step['end_time'].isoformat(),
                    'type': 'StepRandom',
                }
            )

            erase['endTime'] = step['end_time'].isoformat()
            if not erase['startTime']:
                erase['startTime'] = step['start_time'].isoformat()
        return [erase]

    def get_networks(self):
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'network')
        for c in nodes:
            capacity = c.get('capacity')
            units = c.get('units')
            speed = None
            if capacity and units:
                speed = unit.Quantity(capacity, units).to('Mbit/s').m
            wireless = bool(c.get('configuration', {}).get('wireless', False))
            self.components.append(
                {
                    "actions": [],
                    "type": "NetworkAdapter",
                    "model": c.get('product'),
                    "manufacturer": c.get('vendor'),
                    "serialNumber": c.get('serial'),
                    "speed": speed,
                    "variant": c.get('version', 1),
                    "wireless": wireless,
                }
            )

    def get_sound_card(self):
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'multimedia')
        for c in nodes:
            self.components.append(
                {
                    "actions": [],
                    "type": "SoundCard",
                    "model": c.get('product'),
                    "manufacturer": c.get('vendor'),
                    "serialNumber": c.get('serial'),
                }
            )

    def get_display(self):  # noqa: C901
        TECHS = 'CRT', 'TFT', 'LED', 'PDP', 'LCD', 'OLED', 'AMOLED'

        for c in self.monitors:
            resolution_width, resolution_height = (None,) * 2
            refresh, serial, model, manufacturer, size = (None,) * 5
            year, week, production_date = (None,) * 3

            for x in c:
                if "Vendor: " in x:
                    manufacturer = x.split('Vendor: ')[-1].strip()
                if "Model: " in x:
                    model = x.split('Model: ')[-1].strip()
                if "Serial ID: " in x:
                    serial = x.split('Serial ID: ')[-1].strip()
                if "   Resolution: " in x:
                    rs = x.split('   Resolution: ')[-1].strip()
                    if 'x' in rs:
                        resolution_width, resolution_height = [
                            int(r) for r in rs.split('x')
                        ]
                if "Frequencies: " in x:
                    try:
                        refresh = int(float(x.split(',')[-1].strip()[:-3]))
                    except Exception:
                        pass
                if 'Year of Manufacture' in x:
                    year = x.split(': ')[1]

                if 'Week of Manufacture' in x:
                    week = x.split(': ')[1]

                if "Size: " in x:
                    size = self.get_size_monitor(x)
            technology = next((t for t in TECHS if t in c[0]), None)

            if year and week:
                d = '{} {} 0'.format(year, week)
                production_date = datetime.strptime(d, '%Y %W %w').isoformat()

            self.components.append(
                {
                    "actions": [],
                    "type": "Display",
                    "model": model,
                    "manufacturer": manufacturer,
                    "serialNumber": serial,
                    'size': size,
                    'resolutionWidth': resolution_width,
                    'resolutionHeight': resolution_height,
                    "productionDate": production_date,
                    'technology': technology,
                    'refreshRate': refresh,
                }
            )

    def get_hwinfo_monitors(self):
        for c in self.hwinfo:
            monitor = None
            external = None
            for x in c:
                if 'Hardware Class: monitor' in x:
                    monitor = c
                if 'Driver Info' in x:
                    external = c

            if monitor and not external:
                self.monitors.append(c)

    def get_size_monitor(self, x):
        i = 1 / 25.4
        t = x.split('Size: ')[-1].strip()
        tt = t.split('mm')
        if not tt:
            return 0
        sizes = tt[0].strip()
        if 'x' not in sizes:
            return 0
        w, h = [int(x) for x in sizes.split('x')]
        return numpy.sqrt(w**2 + h**2) * i

    def get_cpu_address(self, cpu):
        default = 64
        for ch in self.lshw.get('children', []):
            for c in ch.get('children', []):
                if c['class'] == 'processor':
                    return c.get('width', default)
        return default

    def get_usb_num(self):
        return len(
            [
                u
                for u in self.dmi.get("Port Connector")
                if "USB" in u.get("Port Type", "").upper()
            ]
        )

    def get_serial_num(self):
        return len(
            [
                u
                for u in self.dmi.get("Port Connector")
                if "SERIAL" in u.get("Port Type", "").upper()
            ]
        )

    def get_firmware_num(self):
        return len(
            [
                u
                for u in self.dmi.get("Port Connector")
                if "FIRMWARE" in u.get("Port Type", "").upper()
            ]
        )

    def get_pcmcia_num(self):
        return len(
            [
                u
                for u in self.dmi.get("Port Connector")
                if "PCMCIA" in u.get("Port Type", "").upper()
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
        try:
            memory = ram.get("Size", "0")
            memory = memory.split(' ')
            if len(memory) > 1:
                size = int(memory[0])
                units = memory[1]
                return base2.Quantity(size, units).to('MiB').m
            return int(size.split(" ")[0])
        except Exception as err:
            logger.error("get_ram_size error: {}".format(err))
            return 0

    def get_ram_speed(self, ram):
        size = ram.get("Speed", "0")
        return int(size.split(" ")[0])

    def get_cpu_speed(self, cpu):
        speed = cpu.get('Max Speed', "0")
        return float(speed.split(" ")[0]) / 1024

    def get_sku(self):
        return self.dmi.get("System")[0].get("SKU Number", self.default)

    def get_version(self):
        return self.dmi.get("System")[0].get("Version", self.default)

    def get_uuid(self):
        return self.dmi.get("System")[0].get("UUID", '')

    def get_family(self):
        return self.dmi.get("System")[0].get("Family", '')

    def get_chassis(self):
        return self.dmi.get("Chassis")[0].get("Type", '_virtual')

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

    def get_chassis_dh(self):
        CHASSIS_DH = {
            'Tower': {'desktop', 'low-profile', 'tower', 'server'},
            'Docking': {'docking'},
            'AllInOne': {'all-in-one'},
            'Microtower': {'mini-tower', 'space-saving', 'mini'},
            'PizzaBox': {'pizzabox'},
            'Lunchbox': {'lunchbox'},
            'Stick': {'stick'},
            'Netbook': {'notebook', 'sub-notebook'},
            'Handheld': {'handheld'},
            'Laptop': {'portable', 'laptop'},
            'Convertible': {'convertible'},
            'Detachable': {'detachable'},
            'Tablet': {'tablet'},
            'Virtual': {'_virtual'},
        }

        chassis = self.get_chassis()
        lower_type = chassis.lower()
        for k, v in CHASSIS_DH.items():
            if lower_type in v:
                return k
        return self.default

    def get_data_storage_type(self, x):
        # TODO @cayop add more SSDS types
        SSDS = ["nvme"]
        SSD = 'SolidStateDrive'
        HDD = 'HardDrive'
        type_dev = x.get('device', {}).get('type')
        trim = x.get('trim', {}).get("supported") in [True, "true"]
        return SSD if type_dev in SSDS or trim else HDD

    def get_data_storage_interface(self, x):
        interface = x.get('device', {}).get('protocol', 'ATA')
        try:
            DataStorageInterface(interface.upper())
        except ValueError as err:
            txt = "Sid: {}, interface {} is not in DataStorageInterface Enum".format(
                self.sid, interface
            )
            self.errors("{}".format(err))
            self.errors(txt, severity=Severity.Warning)
        return "ATA"

    def get_data_storage_size(self, x):
        total_capacity = x.get('user_capacity', {}).get('bytes')
        if not total_capacity:
            return 1
        # convert bytes to Mb
        return total_capacity / 1024**2

    def parse_hwinfo(self):
        hw_blocks = self.hwinfo_raw.split("\n\n")
        return [x.split("\n") for x in hw_blocks]

    def loads(self, x):
        if isinstance(x, str):
            return json.loads(x)
        return x

    def errors(self, txt=None, severity=Severity.Error):
        if not txt:
            return self._errors

        logger.error(txt)
        self._errors.append(txt)
        error = SnapshotsLog(
            description=txt,
            snapshot_uuid=self.uuid,
            severity=severity,
            sid=self.sid,
            version=self.version,
        )
        error.save()


class ParseSnapshotLsHw:
    def __init__(self, snapshot, default="n/a"):
        self.default = default
        self.uuid = snapshot.get("uuid")
        self.sid = snapshot.get("sid")
        self.version = str(snapshot.get("version"))
        self.dmidecode_raw = snapshot["hwmd"]["dmidecode"]
        self.smart = snapshot["hwmd"]["smart"]
        self.hwinfo_raw = snapshot["hwmd"]["hwinfo"]
        self.lshw = snapshot["hwmd"]["lshw"]
        self.device = {"actions": []}
        self.components = []
        self.components_obj = []
        self._errors = []

        self.dmi = DMIParse(self.dmidecode_raw)
        self.hwinfo = self.parse_hwinfo()

        self.set_basic_datas()
        self.set_components()

        self.snapshot_json = {
            "type": "Snapshot",
            "device": self.device,
            "software": "Workbench",
            "components": self.components,
            "uuid": snapshot['uuid'],
            "version": "14.0.0",
            "settings_version": snapshot.get("settings_version"),
            "endTime": snapshot["timestamp"],
            "elapsed": 1,
            "sid": snapshot["sid"],
        }

    def get_snapshot(self):
        return Snapshot().load(self.snapshot_json)

    def parse_hwinfo(self):
        hw_blocks = self.hwinfo_raw.split("\n\n")
        return [x.split("\n") for x in hw_blocks]

    def loads(self, x):
        if isinstance(x, str):
            return json.loads(x)
        return x

    def set_basic_datas(self):
        try:
            pc, self.components_obj = Computer.run(
                self.lshw, self.hwinfo_raw, self.uuid, self.sid, self.version
            )
            pc = pc.dump()
            minimum_hid = None in [pc['manufacturer'], pc['model'], pc['serialNumber']]
            if minimum_hid and not self.components_obj:
                # if no there are hid and any components return 422
                raise Exception
        except Exception:
            msg = """It has not been possible to create the device because we lack data.
                You can find more information at: {}""".format(
                request.url_root
            )
            txt = json.dumps({'sid': self.sid, 'message': msg})
            raise ValidationError(txt)

        self.device = pc
        self.device['system_uuid'] = self.get_uuid()

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
            if ram.get('size') == 'No Module Installed':
                continue
            if not ram.get("Speed"):
                continue

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
        size = ram.get("Size")
        if not len(size.split(" ")) == 2:
            txt = (
                "Error: Snapshot: {uuid}, Sid: {sid} have this ram Size: {size}".format(
                    uuid=self.uuid, size=size, sid=self.sid
                )
            )
            self.errors(txt, severity=Severity.Warning)
            return 128
        size, units = size.split(" ")
        return base2.Quantity(float(size), units).to('MiB').m

    def get_ram_speed(self, ram):
        speed = ram.get("Speed", "100")
        if not len(speed.split(" ")) == 2:
            txt = "Error: Snapshot: {uuid}, Sid: {sid} have this ram Speed: {speed}".format(
                uuid=self.uuid, speed=speed, sid=self.sid
            )
            self.errors(txt, severity=Severity.Warning)
            return 100
        speed, units = speed.split(" ")
        return float(speed)
        # TODO @cayop is neccesary change models for accept sizes more high of speed or change to string
        # return base2.Quantity(float(speed), units).to('MHz').m

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

    def get_uuid(self):
        dmi_uuid = 'undefined'
        if self.dmi.get("System"):
            dmi_uuid = self.dmi.get("System")[0].get("UUID")

        try:
            uuid.UUID(dmi_uuid)
        except (ValueError, AttributeError) as err:
            self.errors("{}".format(err))
            txt = "Error: Snapshot: {uuid} sid: {sid} have this uuid: {device}".format(
                uuid=self.uuid, device=dmi_uuid, sid=self.sid
            )
            self.errors(txt, severity=Severity.Warning)
            dmi_uuid = None
        return dmi_uuid

    def get_data_storage(self):
        for sm in self.smart:
            if sm.get('smartctl', {}).get('exit_status') == 1:
                continue
            model = sm.get('model_name')
            manufacturer = None
            if model and len(model.split(" ")) > 1:
                mm = model.split(" ")
                model = mm[-1]
                manufacturer = " ".join(mm[:-1])

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
        trim = x.get('trim', {}).get("supported") in [True, "true"]
        return SSD if type_dev in SSDS or trim else HDD

    def get_data_storage_interface(self, x):
        interface = x.get('device', {}).get('protocol', 'ATA')
        try:
            DataStorageInterface(interface.upper())
        except ValueError as err:
            txt = "Sid: {}, interface {} is not in DataStorageInterface Enum".format(
                self.sid, interface
            )
            self.errors("{}".format(err))
            self.errors(txt, severity=Severity.Warning)
        return "ATA"

    def get_data_storage_size(self, x):
        total_capacity = x.get('user_capacity', {}).get('bytes')
        if not total_capacity:
            return 1
        # convert bytes to Mb
        return total_capacity / 1024**2

    def get_test_data_storage(self, smart):
        hours = smart.get("power_on_time", {}).get('hours', 0)
        action = {
            "status": "Completed without error",
            "reallocatedSectorCount": smart.get("reallocated_sector_count", 0),
            "currentPendingSectorCount": smart.get("current_pending_sector_count", 0),
            "assessment": True,
            "severity": "Info",
            "offlineUncorrectable": smart.get("offline_uncorrectable", 0),
            "lifetime": hours,
            "powerOnHours": hours,
            "type": "TestDataStorage",
            "length": "Short",
            "elapsed": 0,
            "reportedUncorrectableErrors": smart.get(
                "reported_uncorrectable_errors", 0
            ),
            "powerCycleCount": smart.get("power_cycle_count", 0),
        }

        return action

    def get_hid_datas(self):
        self.device.family = self.get_family()

    def get_family(self):
        return self.dmi.get("System", [{}])[0].get("Family", '')

    def errors(self, txt=None, severity=Severity.Error):
        if not txt:
            return self._errors

        logger.error(txt)
        self._errors.append(txt)
        error = SnapshotsLog(
            description=txt,
            snapshot_uuid=self.uuid,
            severity=severity,
            sid=self.sid,
            version=self.version,
        )
        error.save()
