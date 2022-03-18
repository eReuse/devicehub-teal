from dmidecode import DMIParse


class Demidecode:
    def __init__(self, raw, default="n/a"):
        self.default = default
        self.raw = raw
        self.dmi = DMIParse(raw)
        self.device = {"actions": []}
        self.components = []
        self.set_basic_datas()
        self.computer = {
            "device": self.device,
            "software": "Workbench",
            "components": self.components(),
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

    def get_cpu(self):
        cpu = self.dmi.get('Processor')[0]

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
        # TODO @cayop generation, brand and address not exist in dmidecode

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
