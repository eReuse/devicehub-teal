""" This file frame a correct row for csv report """

from collections import OrderedDict
from flask import url_for

from ereuse_devicehub.resources.enums import Severity
from ereuse_devicehub.resources.device import models as d, states
from ereuse_devicehub.resources.action.models import (BenchmarkDataStorage, RateComputer,
                                                      TestDataStorage)


class DeviceRow(OrderedDict):
    NUMS = {
        d.Display.t: 1,
        d.Processor.t: 2,
        d.GraphicCard.t: 2,
        d.Motherboard.t: 1,
        d.NetworkAdapter.t: 2,
        d.SoundCard.t: 2,
        d.RamModule.t: 4,
        d.DataStorage: 5,
    }
    ORDER_COMPONENTS = [
        d.Processor.t,
        d.RamModule.t,
        d.DataStorage.t,
        d.Motherboard.t,
        d.Display.t,
        d.GraphicCard.t,
        d.NetworkAdapter.t,
        d.SoundCard.t,
    ]

    # TODO Add more fields information
    def __init__(self, device: d.Device) -> None:
        super().__init__()
        self.device = device
        # General information about device
        self['System ID'] = device.id
        self['Public Link'] = '{url}{id}'.format(url=url_for('Device.main', _external=True),
                id=device.id)
        self['Tag 1 Type'] = self['Tag 1 ID'] = self['Tag 1 Organization'] = ''
        self['Tag 2 Type'] = self['Tag 2 ID'] = self['Tag 2 Organization'] = ''
        self['Tag 3 Type'] = self['Tag 3 ID'] = self['Tag 3 Organization'] = ''
        for i, tag in zip(range(1, 3), device.tags):
            # TODO @cayop we need redefined how save the Tag Type info
            self['Tag {} Type'.format(i)] = 'unamed'
            self['Tag {} ID'.format(i)] = tag.id
            self['Tag {} Organization'.format(i)] = tag.org.name

        self['Hardware ID'] = device.hid
        self['Device Type'] = device.t
        self['Device Chassis'] = ''
        if isinstance(device, d.Computer):
            self['Chassis'] = device.chassis
        self['Serial Number'] = none2str(device.serial_number)
        self['Model'] = none2str(device.model)
        self['Manufacturer'] = none2str(device.manufacturer)
        self['Registered in'] = format(device.created, '%c')
        # TODO @cayop we need redefined how save in actions the origin of the action
        self['Registered (process)'] = 'Workbench 11.0'
        self['Updated in (software)'] = device.updated
        self['Updated in (web)'] = ''

        try:
            self['Physical state'] = device.last_action_of(*states.Physical.actions()).t
        except LookupError:
            self['Physical state'] = ''
        try:
            self['Trading state'] = device.last_action_of(*states.Trading.actions()).t
        except LookupError:
            self['Trading state'] = ''
        self['Price'] = none2str(device.price)
        if isinstance(device, d.Computer):
            self['Processor'] = none2str(device.processor_model)
            self['RAM (MB)'] = none2str(device.ram_size)
            self['Data Storage Size (MB)'] = none2str(device.data_storage_size)
        # More specific information about components
        if isinstance(device, d.Computer):
            self.components()
        else:
            # TODO @cayop we need add columns as a component
            pass

        rate = device.rate
        if rate:
            self['Device Rate'] = rate.rating
            self['Device Range'] = rate.rating_range
            assert isinstance(rate, RateComputer)
            self['Processor Rate'] = rate.processor
            self['Processor Range'] = rate.processor_range
            self['RAM Rate'] = rate.ram
            self['RAM Range'] = rate.ram_range
            self['Data Storage Rate'] = rate.data_storage
            self['Data Storage Range'] = rate.data_storage_range

    def components(self):
        """Function to get all components information of a device."""
        assert isinstance(self.device, d.Computer)
        for ctype in self.ORDER_COMPONENTS: # ctype: str
            cmax = self.NUMS.get(ctype, 4)
            i = 1
            # import pdb; pdb.set_trace()
            l_ctype = [ctype]
            if ctype == d.DataStorage.t:
                l_ctype = [ctype, d.HardDrive.t, d.SolidStateDrive.t]
            for component in (r for r in self.device.components if r.type in l_ctype):
                self.fill_component(ctype, i, component)
                i += 1
                if i > cmax:
                    break
            while i <= cmax:
                self.fill_component(ctype, i)
                i += 1

    def fill_component(self, ctype, i, component=None):
        """Function to put specific information of components
        in OrderedDict (csv)
        :param ctype: type of component
        :param component: device.components
        """
        # Basic fields for all components
        # import pdb; pdb.set_trace()
        # print(ctype + '| ' + format(component))
        self['{} {}'.format(ctype, i)] = format(component) if component else ''
        if component is None:
            self['{} {} Manufacturer'.format(ctype, i)] = ''
            self['{} {} Model'.format(ctype, i)] = ''
            self['{} {} Serial Number'.format(ctype, i)] = ''
        else:
            self['{} {} Manufacturer'.format(ctype, i)] = none2str(component.manufacturer)
            self['{} {} Model'.format(ctype, i)] = none2str(component.model)
            self['{} {} Serial Number'.format(ctype, i)] = none2str(component.serial_number)

        if ctype == d.Processor.t:
            self.get_processor(ctype, i, component)

        if ctype == d.DataStorage.t:
            self.get_datastorage(ctype, i, component)


        """Particular fields for component GraphicCard."""
        if isinstance(component, d.GraphicCard):
            self['{} {} Memory (MB)'.format(ctype, i)] = component.memory

        """Particular fields for component DataStorage.t -> 
        (HardDrive, SolidStateDrive)
        """
        if isinstance(component, d.DataStorage):
            self['{} {} Size (MB)'.format(ctype, i)] = component.size
            self['{} {} Privacy'.format(ctype, i)] = component.privacy
            try:
                self['{} {} Lifetime'.format(ctype, i)] = component.last_action_of(
                    TestDataStorage).lifetime
            except:
                self['{} {} Lifetime'.format(ctype, i)] = ''


        """Particular fields for component RamModule."""
        if isinstance(component, d.RamModule):
            self['{} {} Size (MB)'.format(ctype, i)] = component.size
            self['{} {} Speed (MHz)'.format(ctype, i)] = component.speed

        # todo add Display, NetworkAdapter, etc...


    def get_processor(self, ctype, i, component):
        """Particular fields for component Processor."""
        if not component is None:
            self['{} {} Number of cores'.format(ctype, i)] = none2str(component.cores)
            self['{} {} Speed (GHz)'.format(ctype, i)] = none2str(component.speed)
        else:
            self['{} {} Number of cores'.format(ctype, i)] = ''
            self['{} {} Speed (GHz)'.format(ctype, i)] = ''

    def get_datastorage(self, ctype, i, component):
        """Particular fields for component DataStorage.
           A DataStorage can be HardDrive or SolidStateDrive.
        """
        if component is None:
            self['{} {} Size'.format(ctype, i)] = ''
            self['Erasure {} {}'.format(ctype, i)] = ''
            self['Erasure {} {} Serial Number'.format(ctype, i)] = ''
            self['Erasure {} {} Size'.format(ctype, i)] = ''
            self['Erasure {} {} Software'.format(ctype, i)] = ''
            self['Erasure {} {} Result'.format(ctype, i)] = ''
            self['Erasure {} {} Type'.format(ctype, i)] = ''
            self['Erasure {} {} Method'.format(ctype, i)] = ''
            self['Erasure {} {} Elapsed'.format(ctype, i)] = ''
            self['Erasure {} {} Date'.format(ctype, i)] = ''
            self['Erasure {} {} Steps'.format(ctype, i)] = ''
            self['Erasure {} {} Steps Start Time'.format(ctype, i)] = ''
            self['Erasure {} {} Steps End Time'.format(ctype, i)] = ''
            self['Benchmark {} {} Read Speed (MB/s)'.format(ctype, i)] = ''
            self['Benchmark {} {} Writing speed (MB/s)'.format(ctype, i)] = ''
            return

        self['{} {} Size'.format(ctype, i)] = none2str(component.size)

        erasures = [a for a in component.actions if a.type in ['EraseBasic', 'EraseSectors']]
        erasure = erasures[-1] if erasures else None
        if not erasure:
            self['Erasure {} {}'.format(ctype, i)] = none2str(component.hid)
            serial_number = none2str(component.serial_number)
            self['Erasure {} {} Serial Number'.format(ctype, i)] = serial_number
            self['Erasure {} {} Size'.format(ctype, i)] = none2str(component.size)
            self['Erasure {} {} Software'.format(ctype, i)] = ''
            self['Erasure {} {} Result'.format(ctype, i)] = ''
            self['Erasure {} {} Type'.format(ctype, i)] = ''
            self['Erasure {} {} Method'.format(ctype, i)] = ''
            self['Erasure {} {} Elapsed'.format(ctype, i)] = ''
            self['Erasure {} {} Date'.format(ctype, i)] = ''
            self['Erasure {} {} Steps'.format(ctype, i)] = ''
            self['Erasure {} {} Steps Start Time'.format(ctype, i)] = ''
            self['Erasure {} {} Steps End Time'.format(ctype, i)] = ''
            self['Benchmark {} {} Read Speed (MB/s)'.format(ctype, i)] = ''
            self['Benchmark {} {} Writing speed (MB/s)'.format(ctype, i)] = ''
            return


        self['Erasure {} {}'.format(ctype, i)] = none2str(component.hid)
        serial_number = none2str(component.serial_number)
        self['Erasure {} {} Serial Number'.format(ctype, i)] = serial_number
        self['Erasure {} {} Size'.format(ctype, i)] = none2str(component.size)
        # TODO @cayop This line is hardcoded we need change this in the future
        self['Erasure {} {} Software'.format(ctype, i)] = 'Workbench 11.0'

        result = get_result_erasure(erasure.severity)
        self['Erasure {} {} Result'.format(ctype, i)] = result
        self['Erasure {} {} Type'.format(ctype, i)] = erasure.type
        self['Erasure {} {} Method'.format(ctype, i)] = erasure.method
        self['Erasure {} {} Elapsed'.format(ctype, i)] = format(erasure.elapsed)
        self['Erasure {} {} Date'.format(ctype, i)] = format(erasure.created)
        steps = ','.join((format(x) for x in erasure.steps))
        self['Erasure {} {} Steps'.format(ctype, i)] = steps
        steps_start_time = ','.join((format(x.start_time) for x in erasure.steps))
        self['Erasure {} {} Steps Start Time'.format(ctype, i)] = steps_start_time
        steps_end_time = ','.join((format(x.end_time) for x in erasure.steps))
        self['Erasure {} {} Steps End Time'.format(ctype, i)] = steps_end_time

        benchmarks = [a for a in component.actions if a.type == 'BenchmarkDataStorage']
        benchmark = benchmarks[-1] if benchmarks else None
        if not benchmark:
            self['Benchmark {} {} Read Speed (MB/s)'.format(ctype, i)] = ''
            self['Benchmark {} {} Writing speed (MB/s)'.format(ctype, i)] = ''
            return

        self['Benchmark {} {} Read Speed (MB/s)'.format(ctype, i)] = benchmark.read_speed
        self['Benchmark {} {} Writing speed (MB/s)'.format(ctype, i)] = benchmark.write_speed


class StockRow(OrderedDict):
    def __init__(self, device: d.Device) -> None:
        super().__init__()
        self.device = device
        self['Type'] = none2str(device.t)
        if isinstance(device, d.Computer):
            self['Chassis'] = device.chassis
        else:
            self['Chassis'] = ''
        self['Serial Number'] = none2str(device.serial_number)
        self['Model'] = none2str(device.model)
        self['Manufacturer'] = none2str(device.manufacturer)
        self['Registered in'] = format(device.created, '%c')
        try:
            self['Physical state'] = device.last_action_of(*states.Physical.actions()).t
        except LookupError:
            self['Physical state'] = ''
        try:
            self['Trading state'] = device.last_action_of(*states.Trading.actions()).t
        except LookupError:
            self['Trading state'] = ''
            self['Price'] = none2str(device.price)
            self['Processor'] = none2str(device.processor_model)
            self['RAM (MB)'] = none2str(device.ram_size)
            self['Data Storage Size (MB)'] = none2str(device.data_storage_size)
        rate = device.rate
        if rate:
            self['Rate'] = rate.rating
            self['Range'] = rate.rating_range
            assert isinstance(rate, RateComputer)
            self['Processor Rate'] = rate.processor
            self['Processor Range'] = rate.processor_range
            self['RAM Rate'] = rate.ram
            self['RAM Range'] = rate.ram_range
            self['Data Storage Rate'] = rate.data_storage
            self['Data Storage Range'] = rate.data_storage_range


def get_result_erasure(severity):
    """ For the csv is necessary simplify the message of results """
    type_of_results = {
        Severity.Error: 'Failure',
        Severity.Warning: 'Success with Warnings',
        Severity.Notice: 'Success',
        Severity.Info: 'Success'
        }
    return type_of_results[severity]


def none2str(string):
    """ convert none to empty str """
    if string is None:
        return ''
    return string
