from collections import OrderedDict

from flask import current_app

from ereuse_devicehub.resources.device import models as d
from ereuse_devicehub.resources.event.models import TestDataStorage, BenchmarkDataStorage


class DeviceRow(OrderedDict):
    NUMS = {
        d.Display.t: 1,
        d.Processor.t: 2,
        d.GraphicCard.t: 2,
        d.Motherboard.t: 1,
        d.NetworkAdapter.t: 2,
        d.SoundCard.t: 2
    }

    # TODO Add more fields information
    def __init__(self, device: d.Device) -> None:
        super().__init__()
        self.device = device
        # General information about device
        self['Type'] = device.t
        if isinstance(device, d.Computer):
            self['Chassis'] = device.chassis
        else:
            self['Chassis'] = ''
        self['Tag 1'] = self['Tag 2'] = self['Tag 3'] = ''
        for i, tag in zip(range(1, 3), device.tags):
            self['Tag {}'.format(i)] = format(tag)
        self['Serial Number'] = device.serial_number
        self['Model'] = device.model
        self['Manufacturer'] = device.manufacturer
        # self['State'] = device.last_event_of()
        self['Registered in'] = format(device.created, '%c')
        self['Price'] = device.price
        if isinstance(device, d.Computer):
            self['Processor'] = device.processor_model
            self['RAM (GB)'] = device.ram_size
            self['Data Storage Size (MB)'] = device.data_storage_size
        rate = device.rate
        if rate:
            self['Rate'] = rate.rating
            self['Range'] = rate.rating_range
            self['Processor Rate'] = rate.processor
            self['Processor Range'] = rate.workbench.processor_range
            self['RAM Rate'] = rate.ram
            self['RAM Range'] = rate.workbench.ram_range
            self['Data Storage Rate'] = rate.data_storage
            self['Data Storage Range'] = rate.workbench.data_storage_range
        # More specific information about components
        if isinstance(device, d.Computer):
            self.components()

    def components(self):
        """
        Function to get all components information of a device
        """
        assert isinstance(self.device, d.Computer)
        # todo put an input specific order (non alphabetic) & where are a list of types components
        for type in sorted(current_app.resources[d.Component.t].subresources_types):  # type: str
            max = self.NUMS.get(type, 4)
            if type not in ['Component', 'HardDrive', 'SolidStateDrive']:
                i = 1
                for component in (r for r in self.device.components if r.type == type):
                    self.fill_component(type, i, component)
                    i += 1
                    if i > max:
                        break
                while i <= max:
                    self.fill_component(type, i)
                    i += 1

    def fill_component(self, type, i, component=None):
        """
        Function to put specific information of components in OrderedDict (csv)
        :param type: type of component
        :param component: device.components
        """
        self['{} {}'.format(type, i)] = format(component) if component else ''
        self['{} {} Manufacturer'.format(type, i)] = component.serial_number if component else ''
        self['{} {} Model'.format(type, i)] = component.serial_number if component else ''
        self['{} {} Serial Number'.format(type, i)] = component.serial_number if component else ''

        """ Particular fields for component GraphicCard """
        if isinstance(component, d.GraphicCard):
            self['{} {} Memory (MB)'.format(type, i)] = component.memory

        """ Particular fields for component DataStorage.t -> (HardDrive, SolidStateDrive) """
        if isinstance(component, d.DataStorage):
            self['{} {} Size (MB)'.format(type, i)] = component.size
            self['{} {} Privacy'.format(type, i)] = component.privacy
            try:
                self['{} {} Lifetime'.format(type, i)] = component.last_event_of(TestDataStorage).lifetime
            except:
                self['{} {} Lifetime'.format(type, i)] = ''
            try:
                self['{} {} Reading speed'.format(type, i)] = component.last_event_of(BenchmarkDataStorage).read_speed
            except:
                self['{} {} Reading speed'.format(type, i)] = ''
            try:
                self['{} {} Writing speed'.format(type, i)] = component.last_event_of(BenchmarkDataStorage).write_speed
            except:
                self['{} {} Writing speed'.format(type, i)] = ''

        """ Particular fields for component Processor """
        if isinstance(component, d.Processor):
            self['{} {} Number of cores'.format(type, i)] = component.cores
            self['{} {} Speed (GHz)'.format(type, i)] = component.speed

        """ Particular fields for component RamModule """
        if isinstance(component, d.RamModule):
            self['{} {} Size (MB)'.format(type, i)] = component.size
            self['{} {} Speed (MHz)'.format(type, i)] = component.speed

        # todo add Display size, ...
        # todo add NetworkAdapter speedLink?
        # todo add some ComputerAccessories
