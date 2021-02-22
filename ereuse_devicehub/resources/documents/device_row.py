""" This file frame a correct row for csv report """

from collections import OrderedDict
from flask import url_for

from ereuse_devicehub.resources.enums import Severity
from ereuse_devicehub.resources.device import models as d, states
from ereuse_devicehub.resources.action import models as da
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

    def __init__(self, device: d.Device, document_ids: dict) -> None:
        super().__init__()
        self.device = device
        self.document_id = document_ids.get(device.id, '')
        snapshot = get_action(device, 'Snapshot')
        software = ''
        if snapshot:
            software = "{software} {version}".format(
                software=snapshot.software.name, version=snapshot.version)
        # General information about device
        self['System ID'] = device.id
        self['DocumentID'] = self.document_id
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

        self['Device Hardware ID'] = device.hid
        self['Device Type'] = device.t
        self['Device Chassis'] = ''
        if isinstance(device, d.Computer):
            self['Device Chassis'] = device.chassis.name
        self['Device Serial Number'] = none2str(device.serial_number)
        self['Device Model'] = none2str(device.model)
        self['Device Manufacturer'] = none2str(device.manufacturer)
        self['Registered in'] = format(device.created, '%c')
        self['Registered (process)'] = software
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
            self['Device Range'] = rate.rating_range.name
            assert isinstance(rate, RateComputer)
            self['Processor Rate'] = rate.processor
            self['Processor Range'] = rate.processor_range.name
            self['RAM Rate'] = rate.ram
            self['RAM Range'] = rate.ram_range.name
            self['Data Storage Rate'] = rate.data_storage
            self['Data Storage Range'] = rate.data_storage_range.name
        else:
            self['Device Rate'] = ''
            self['Device Range'] = ''
            self['Processor Rate'] = ''
            self['Processor Range'] = ''
            self['RAM Rate'] = ''
            self['RAM Range'] = ''
            self['Data Storage Rate'] = ''
            self['Data Storage Range'] = ''
        
        self['Price'] = none2str(device.price)

        benchram = get_action(device, 'BenchmarkRamSysbench')
        if benchram:
            self['Benchmark RamSysbench (points)'] = none2str(benchram.rate)
        else:
            self['Benchmark RamSysbench (points)'] = ''

    def components(self):
        """Function to get all components information of a device."""
        assert isinstance(self.device, d.Computer)
        for ctype in self.ORDER_COMPONENTS: # ctype: str
            cmax = self.NUMS.get(ctype, 4)
            i = 1
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

        if ctype == d.RamModule.t:
            self.get_ram(ctype, i, component)

        if ctype == d.DataStorage.t:
            self.get_datastorage(ctype, i, component)

        if ctype == d.GraphicCard.t:
            self.get_graphic_card(ctype, i, component)

    def get_processor(self, ctype, i, component):
        """Particular fields for component Processor."""
        if component is None:
            self['{} {} Number of cores'.format(ctype, i)] = ''
            self['{} {} Speed (GHz)'.format(ctype, i)] = ''
            self['Benchmark {} {} (points)'.format(ctype, i)] = ''
            self['Benchmark ProcessorSysbench {} {} (points)'.format(ctype, i)] = ''
            return

        self['{} {} Number of cores'.format(ctype, i)] = none2str(component.cores)
        self['{} {} Speed (GHz)'.format(ctype, i)] = none2str(component.speed)

        benchmark = get_action(component, 'BenchmarkProcessor')
        if not benchmark:
            self['Benchmark {} {} (points)'.format(ctype, i)] = ''
        else:
            self['Benchmark {} {} (points)'.format(ctype, i)] = benchmark.rate

        sysbench = get_action(component, 'BenchmarkProcessorSysbench')
        if not sysbench:
            self['Benchmark ProcessorSysbench {} {} (points)'.format(ctype, i)] = ''
            return
        self['Benchmark ProcessorSysbench {} {} (points)'.format(ctype, i)] = sysbench.rate

    def get_ram(self, ctype, i, component):
        """Particular fields for component Ram Module."""
        if component is None:
            self['{} {} Size (MB)'.format(ctype, i)] = ''
            self['{} {} Speed (MHz)'.format(ctype, i)] = ''
            return

        self['{} {} Size (MB)'.format(ctype, i)] = none2str(component.size)
        self['{} {} Speed (MHz)'.format(ctype, i)] = none2str(component.speed)

    def get_datastorage(self, ctype, i, component):
        """Particular fields for component DataStorage.
           A DataStorage can be HardDrive or SolidStateDrive.
        """
        if component is None:
            self['{} {} Size (MB)'.format(ctype, i)] = ''
            self['Erasure {} {}'.format(ctype, i)] = ''
            self['Erasure {} {} Serial Number'.format(ctype, i)] = ''
            self['Erasure {} {} Size (MB)'.format(ctype, i)] = ''
            self['Erasure {} {} Software'.format(ctype, i)] = ''
            self['Erasure {} {} Result'.format(ctype, i)] = ''
            self['Erasure {} {} Type'.format(ctype, i)] = ''
            self['Erasure {} {} Method'.format(ctype, i)] = ''
            self['Erasure {} {} Elapsed (hours)'.format(ctype, i)] = ''
            self['Erasure {} {} Date'.format(ctype, i)] = ''
            self['Erasure {} {} Steps'.format(ctype, i)] = ''
            self['Erasure {} {} Steps Start Time'.format(ctype, i)] = ''
            self['Erasure {} {} Steps End Time'.format(ctype, i)] = ''
            self['Benchmark {} {} Read Speed (MB/s)'.format(ctype, i)] = ''
            self['Benchmark {} {} Writing speed (MB/s)'.format(ctype, i)] = ''
            self['Test {} {} Software'.format(ctype, i)] = ''
            self['Test {} {} Type'.format(ctype, i)] = ''
            self['Test {} {} Result'.format(ctype, i)] = ''
            self['Test {} {} Power on (hours used)'.format(ctype, i)] = ''
            self['Test {} {} Lifetime remaining (percentage)'.format(ctype, i)] = ''
            return

        snapshot = get_action(component, 'Snapshot')
        software = ''
        if snapshot:
            software = "{software} {version}".format(
                software=snapshot.software.name, version=snapshot.version)

        self['{} {} Size (MB)'.format(ctype, i)] = none2str(component.size)

        erasures = [a for a in component.actions if a.type in ['EraseBasic', 'EraseSectors']]
        erasure = erasures[-1] if erasures else None
        if not erasure:
            self['Erasure {} {}'.format(ctype, i)] = none2str(component.hid)
            serial_number = none2str(component.serial_number)
            self['Erasure {} {} Serial Number'.format(ctype, i)] = serial_number
            self['Erasure {} {} Size (MB)'.format(ctype, i)] = none2str(component.size)
            self['Erasure {} {} Software'.format(ctype, i)] = ''
            self['Erasure {} {} Result'.format(ctype, i)] = ''
            self['Erasure {} {} Type'.format(ctype, i)] = ''
            self['Erasure {} {} Method'.format(ctype, i)] = ''
            self['Erasure {} {} Elapsed (hours)'.format(ctype, i)] = ''
            self['Erasure {} {} Date'.format(ctype, i)] = ''
            self['Erasure {} {} Steps'.format(ctype, i)] = ''
            self['Erasure {} {} Steps Start Time'.format(ctype, i)] = ''
            self['Erasure {} {} Steps End Time'.format(ctype, i)] = ''
        else:
            self['Erasure {} {}'.format(ctype, i)] = none2str(component.hid)
            serial_number = none2str(component.serial_number)
            self['Erasure {} {} Serial Number'.format(ctype, i)] = serial_number
            self['Erasure {} {} Size (MB)'.format(ctype, i)] = none2str(component.size)
            self['Erasure {} {} Software'.format(ctype, i)] = software

            result = get_result(erasure.severity)
            self['Erasure {} {} Result'.format(ctype, i)] = result
            self['Erasure {} {} Type'.format(ctype, i)] = erasure.type
            self['Erasure {} {} Method'.format(ctype, i)] = erasure.method
            self['Erasure {} {} Elapsed (hours)'.format(ctype, i)] = format(erasure.elapsed)
            self['Erasure {} {} Date'.format(ctype, i)] = format(erasure.created)
            steps = ','.join((format(x) for x in erasure.steps))
            self['Erasure {} {} Steps'.format(ctype, i)] = steps
            steps_start_time = ','.join((format(x.start_time) for x in erasure.steps))
            self['Erasure {} {} Steps Start Time'.format(ctype, i)] = steps_start_time
            steps_end_time = ','.join((format(x.end_time) for x in erasure.steps))
            self['Erasure {} {} Steps End Time'.format(ctype, i)] = steps_end_time

        benchmark = get_action(component, 'BenchmarkDataStorage')
        if not benchmark:
            self['Benchmark {} {} Read Speed (MB/s)'.format(ctype, i)] = ''
            self['Benchmark {} {} Writing speed (MB/s)'.format(ctype, i)] = ''
        else:
            self['Benchmark {} {} Read Speed (MB/s)'.format(ctype, i)] = none2str(
                benchmark.read_speed)
            self['Benchmark {} {} Writing speed (MB/s)'.format(ctype, i)] = none2str(
                benchmark.write_speed)

        test_storage = get_action(component, 'TestDataStorage')
        if not test_storage:
            self['Test {} {} Software'.format(ctype, i)] = ''
            self['Test {} {} Type'.format(ctype, i)] = ''
            self['Test {} {} Result'.format(ctype, i)] = ''
            self['Test {} {} Power on (hours used)'.format(ctype, i)] = ''
            self['Test {} {} Lifetime remaining (percentage)'.format(ctype, i)] = ''
            return

        self['Test {} {} Software'.format(ctype, i)] = software
        self['Test {} {} Type'.format(ctype, i)] = test_storage.length.value
        self['Test {} {} Result'.format(ctype, i)] = get_result(test_storage.severity)
        self['Test {} {} Power on (hours used)'.format(ctype, i)] = none2str(
            test_storage.power_cycle_count)
        self['Test {} {} Lifetime remaining (percentage)'.format(ctype, i)] = none2str(
            test_storage.lifetime)

    def get_graphic_card(self, ctype, i, component):
        """Particular fields for component GraphicCard."""
        if component is None:
            self['{} {} Memory (MB)'.format(ctype, i)] = ''
            return

        self['{} {} Memory (MB)'.format(ctype, i)] = none2str(component.memory)


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


def get_result(severity):
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
    return format(string)

def get_action(component, action):
    """ Filter one action from a component or return None """
    result = [a for a in component.actions if a.type == action]
    return result[-1] if result else None


class ActionRow(OrderedDict):

    def __init__(self, allocate): 
        super().__init__()
        # General information about allocates, deallocate and lives
        self['SystemId'] = allocate['systemId']
        self['Hid'] = allocate['hid']
        self['Start'] = allocate['start']
        self['FinalUserCode'] = allocate['finalUserCode']
        self['NumEndUsers'] = allocate['numEndUsers']
        self['UsageTimeAllocate'] = allocate['usageTimeAllocate']
        self['Type'] = allocate['type']
        self['LiveCreate'] = allocate['liveCreate']
        self['UsageTimeHdd'] = allocate['usageTimeHdd']


class InternalStatsRow(OrderedDict):

    def __init__(self, user, create, actions):
        super().__init__()
        # General information about all internal stats
        # user, quart, month, year:
        #    Snapshot (Registers)
        #    Snapshots (Update)
        #    Snapshots (All)
        #    Allocate
        #    Deallocate
        #    Live
        self.actions = actions
        year, month = create.split('-')

        self['User'] = user
        self['Year'] = year
        self['Quarter'] = self.quarter(month)
        self['Month'] = month
        self['Snapshot (Registers)'] = 0
        self['Snapshot (Update)'] = 0
        self['Snapshot (All)'] = 0
        self['Allocates'] = 0
        self['Deallocates'] = 0
        self['Lives'] = 0

        self.count_actions()

    def count_actions(self):
        for ac in self.actions:
            self.is_snapshot(
                self.is_deallocate(
                    self.is_allocate(ac)
                )
            )

    def is_allocate(self, ac):
        if ac.type == 'Allocate':
            self['Allocates'] += 1
        return ac

    def is_deallocate(self, ac):
        if ac.type == 'Deallocate':
            self['Deallocates'] += 1
        return ac

    def is_snapshot(self, ac):
        if not ac.type == 'Snapshot':
            return
        self['Snapshot (All)'] += 1

        canary = False
        for _ac in ac.device.actions:
            if _ac.created < ac.created:
                canary = True
                break

        if canary:
            self['Snapshot (Update)'] += 1
        else:
            self['Snapshot (Registers)'] += 1

    def quarter(self, month):
        q = {1: 'Q1', 2: 'Q1', 3: 'Q1',
             4: 'Q2', 5: 'Q2', 6: 'Q2',
             7: 'Q3', 8: 'Q3', 9: 'Q3',
             10: 'Q4', 11: 'Q4', 12: 'Q4',
             }
        return q[int(month)]
