""" This file frame a correct row for csv report """

from collections import OrderedDict

from flask import url_for

from ereuse_devicehub.resources.action.models import RateComputer
from ereuse_devicehub.resources.device import models as d
from ereuse_devicehub.resources.device import states
from ereuse_devicehub.resources.enums import Severity


class BaseDeviceRow(OrderedDict):
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

    def __init__(self) -> None:
        super().__init__()
        self['DHID'] = ''
        self['DocumentID'] = ''
        self['Public Link'] = ''
        self['Lots'] = ''
        self['Tag 1 Type'] = ''
        self['Tag 1 ID'] = ''
        self['Tag 1 Organization'] = ''
        self['Tag 2 Type'] = ''
        self['Tag 2 ID'] = ''
        self['Tag 2 Organization'] = ''
        self['Tag 3 Type'] = ''
        self['Tag 3 ID'] = ''
        self['Tag 3 Organization'] = ''
        self['Device Hardware ID'] = ''
        self['Device Type'] = ''
        self['Device Chassis'] = ''
        self['Device Serial Number'] = ''
        self['Device Model'] = ''
        self['Device Manufacturer'] = ''
        self['Registered in'] = ''
        self['Registered (process)'] = ''
        self['Updated in (software)'] = ''
        self['Updated in (web)'] = ''
        self['Physical state'] = ''
        self['Allocate state'] = ''
        self['Lifecycle state'] = ''
        self['Processor'] = ''
        self['RAM (MB)'] = ''
        self['Data Storage Size (MB)'] = ''
        self['Processor 1'] = ''
        self['Processor 1 Manufacturer'] = ''
        self['Processor 1 Model'] = ''
        self['Processor 1 Serial Number'] = ''
        self['Processor 1 Number of cores'] = ''
        self['Processor 1 Speed (GHz)'] = ''
        self['Benchmark Processor 1 (points)'] = ''
        self['Benchmark ProcessorSysbench Processor 1 (points)'] = ''
        self['Processor 2'] = ''
        self['Processor 2 Manufacturer'] = ''
        self['Processor 2 Model'] = ''
        self['Processor 2 Serial Number'] = ''
        self['Processor 2 Number of cores'] = ''
        self['Processor 2 Speed (GHz)'] = ''
        self['Benchmark Processor 2 (points)'] = ''
        self['Benchmark ProcessorSysbench Processor 2 (points)'] = ''
        self['RamModule 1'] = ''
        self['RamModule 1 Manufacturer'] = ''
        self['RamModule 1 Model'] = ''
        self['RamModule 1 Serial Number'] = ''
        self['RamModule 1 Size (MB)'] = ''
        self['RamModule 1 Speed (MHz)'] = ''
        self['RamModule 2'] = ''
        self['RamModule 2 Manufacturer'] = ''
        self['RamModule 2 Model'] = ''
        self['RamModule 2 Serial Number'] = ''
        self['RamModule 2 Size (MB)'] = ''
        self['RamModule 2 Speed (MHz)'] = ''
        self['RamModule 3'] = ''
        self['RamModule 3 Manufacturer'] = ''
        self['RamModule 3 Model'] = ''
        self['RamModule 3 Serial Number'] = ''
        self['RamModule 3 Size (MB)'] = ''
        self['RamModule 3 Speed (MHz)'] = ''
        self['RamModule 4'] = ''
        self['RamModule 4 Manufacturer'] = ''
        self['RamModule 4 Model'] = ''
        self['RamModule 4 Serial Number'] = ''
        self['RamModule 4 Size (MB)'] = ''
        self['RamModule 4 Speed (MHz)'] = ''
        self['DataStorage 1'] = ''
        self['DataStorage 1 Manufacturer'] = ''
        self['DataStorage 1 Model'] = ''
        self['DataStorage 1 Serial Number'] = ''
        self['DataStorage 1 Size (MB)'] = ''
        self['Erasure DataStorage 1'] = ''
        self['Erasure DataStorage 1 Serial Number'] = ''
        self['Erasure DataStorage 1 Size (MB)'] = ''
        self['Erasure DataStorage 1 Software'] = ''
        self['Erasure DataStorage 1 Result'] = ''
        self['Erasure DataStorage 1 Certificate URL'] = ''
        self['Erasure DataStorage 1 Type'] = ''
        self['Erasure DataStorage 1 Method'] = ''
        self['Erasure DataStorage 1 Elapsed (hours)'] = ''
        self['Erasure DataStorage 1 Date'] = ''
        self['Erasure DataStorage 1 Steps'] = ''
        self['Erasure DataStorage 1 Steps Start Time'] = ''
        self['Erasure DataStorage 1 Steps End Time'] = ''
        self['Benchmark DataStorage 1 Read Speed (MB/s)'] = ''
        self['Benchmark DataStorage 1 Writing speed (MB/s)'] = ''
        self['Test DataStorage 1 Software'] = ''
        self['Test DataStorage 1 Type'] = ''
        self['Test DataStorage 1 Result'] = ''
        self['Test DataStorage 1 Power cycle count'] = ''
        self['Test DataStorage 1 Lifetime (days)'] = ''
        self['Test DataStorage 1 Power on hours'] = ''
        self['DataStorage 2'] = ''
        self['DataStorage 2 Manufacturer'] = ''
        self['DataStorage 2 Model'] = ''
        self['DataStorage 2 Serial Number'] = ''
        self['DataStorage 2 Size (MB)'] = ''
        self['Erasure DataStorage 2'] = ''
        self['Erasure DataStorage 2 Serial Number'] = ''
        self['Erasure DataStorage 2 Size (MB)'] = ''
        self['Erasure DataStorage 2 Software'] = ''
        self['Erasure DataStorage 2 Result'] = ''
        self['Erasure DataStorage 2 Certificate URL'] = ''
        self['Erasure DataStorage 2 Type'] = ''
        self['Erasure DataStorage 2 Method'] = ''
        self['Erasure DataStorage 2 Elapsed (hours)'] = ''
        self['Erasure DataStorage 2 Date'] = ''
        self['Erasure DataStorage 2 Steps'] = ''
        self['Erasure DataStorage 2 Steps Start Time'] = ''
        self['Erasure DataStorage 2 Steps End Time'] = ''
        self['Benchmark DataStorage 2 Read Speed (MB/s)'] = ''
        self['Benchmark DataStorage 2 Writing speed (MB/s)'] = ''
        self['Test DataStorage 2 Software'] = ''
        self['Test DataStorage 2 Type'] = ''
        self['Test DataStorage 2 Result'] = ''
        self['Test DataStorage 2 Power cycle count'] = ''
        self['Test DataStorage 2 Lifetime (days)'] = ''
        self['Test DataStorage 2 Power on hours'] = ''
        self['DataStorage 3'] = ''
        self['DataStorage 3 Manufacturer'] = ''
        self['DataStorage 3 Model'] = ''
        self['DataStorage 3 Serial Number'] = ''
        self['DataStorage 3 Size (MB)'] = ''
        self['Erasure DataStorage 3'] = ''
        self['Erasure DataStorage 3 Serial Number'] = ''
        self['Erasure DataStorage 3 Size (MB)'] = ''
        self['Erasure DataStorage 3 Software'] = ''
        self['Erasure DataStorage 3 Result'] = ''
        self['Erasure DataStorage 3 Certificate URL'] = ''
        self['Erasure DataStorage 3 Type'] = ''
        self['Erasure DataStorage 3 Method'] = ''
        self['Erasure DataStorage 3 Elapsed (hours)'] = ''
        self['Erasure DataStorage 3 Date'] = ''
        self['Erasure DataStorage 3 Steps'] = ''
        self['Erasure DataStorage 3 Steps Start Time'] = ''
        self['Erasure DataStorage 3 Steps End Time'] = ''
        self['Benchmark DataStorage 3 Read Speed (MB/s)'] = ''
        self['Benchmark DataStorage 3 Writing speed (MB/s)'] = ''
        self['Test DataStorage 3 Software'] = ''
        self['Test DataStorage 3 Type'] = ''
        self['Test DataStorage 3 Result'] = ''
        self['Test DataStorage 3 Power cycle count'] = ''
        self['Test DataStorage 3 Lifetime (days)'] = ''
        self['Test DataStorage 3 Power on hours'] = ''
        self['DataStorage 4'] = ''
        self['DataStorage 4 Manufacturer'] = ''
        self['DataStorage 4 Model'] = ''
        self['DataStorage 4 Serial Number'] = ''
        self['DataStorage 4 Size (MB)'] = ''
        self['Erasure DataStorage 4'] = ''
        self['Erasure DataStorage 4 Serial Number'] = ''
        self['Erasure DataStorage 4 Size (MB)'] = ''
        self['Erasure DataStorage 4 Software'] = ''
        self['Erasure DataStorage 4 Result'] = ''
        self['Erasure DataStorage 4 Certificate URL'] = ''
        self['Erasure DataStorage 4 Type'] = ''
        self['Erasure DataStorage 4 Method'] = ''
        self['Erasure DataStorage 4 Elapsed (hours)'] = ''
        self['Erasure DataStorage 4 Date'] = ''
        self['Erasure DataStorage 4 Steps'] = ''
        self['Erasure DataStorage 4 Steps Start Time'] = ''
        self['Erasure DataStorage 4 Steps End Time'] = ''
        self['Benchmark DataStorage 4 Read Speed (MB/s)'] = ''
        self['Benchmark DataStorage 4 Writing speed (MB/s)'] = ''
        self['Test DataStorage 4 Software'] = ''
        self['Test DataStorage 4 Type'] = ''
        self['Test DataStorage 4 Result'] = ''
        self['Test DataStorage 4 Power cycle count'] = ''
        self['Test DataStorage 4 Lifetime (days)'] = ''
        self['Test DataStorage 4 Power on hours'] = ''
        self['Motherboard 1'] = ''
        self['Motherboard 1 Manufacturer'] = ''
        self['Motherboard 1 Model'] = ''
        self['Motherboard 1 Serial Number'] = ''
        self['Display 1'] = ''
        self['Display 1 Manufacturer'] = ''
        self['Display 1 Model'] = ''
        self['Display 1 Serial Number'] = ''
        self['GraphicCard 1'] = ''
        self['GraphicCard 1 Manufacturer'] = ''
        self['GraphicCard 1 Model'] = ''
        self['GraphicCard 1 Serial Number'] = ''
        self['GraphicCard 1 Memory (MB)'] = ''
        self['GraphicCard 2'] = ''
        self['GraphicCard 2 Manufacturer'] = ''
        self['GraphicCard 2 Model'] = ''
        self['GraphicCard 2 Serial Number'] = ''
        self['GraphicCard 2 Memory (MB)'] = ''
        self['NetworkAdapter 1'] = ''
        self['NetworkAdapter 1 Manufacturer'] = ''
        self['NetworkAdapter 1 Model'] = ''
        self['NetworkAdapter 1 Serial Number'] = ''
        self['NetworkAdapter 2'] = ''
        self['NetworkAdapter 2 Manufacturer'] = ''
        self['NetworkAdapter 2 Model'] = ''
        self['NetworkAdapter 2 Serial Number'] = ''
        self['SoundCard 1'] = ''
        self['SoundCard 1 Manufacturer'] = ''
        self['SoundCard 1 Model'] = ''
        self['SoundCard 1 Serial Number'] = ''
        self['SoundCard 2'] = ''
        self['SoundCard 2 Manufacturer'] = ''
        self['SoundCard 2 Model'] = ''
        self['SoundCard 2 Serial Number'] = ''
        self['Device Rate'] = ''
        self['Device Range'] = ''
        self['Processor Rate'] = ''
        self['Processor Range'] = ''
        self['RAM Rate'] = ''
        self['RAM Range'] = ''
        self['Data Storage Rate'] = ''
        self['Data Storage Range'] = ''
        self['Benchmark RamSysbench (points)'] = ''
        # Placeholder
        self['PHID'] = ''
        self['Is Abstract'] = ''
        self['Pallet'] = ''
        self['id Supplier'] = ''
        self['Real Info'] = ''
        self['Real Components'] = ''
        self['Real Type'] = ''
        self['Real Serial Number'] = ''
        self['Real Part Number'] = ''
        self['Real Model'] = ''
        self['Real Manufacturer'] = ''


class DeviceRow(BaseDeviceRow):
    def __init__(self, device: d.Device, document_ids: dict) -> None:
        super().__init__()
        self.placeholder = device.binding or device.placeholder
        self.device = self.placeholder.binding or self.placeholder.device
        self.document_id = document_ids.get(device.id, '')
        snapshot = get_action(device, 'Snapshot')
        software = ''
        if snapshot:
            software = "{software} {version}".format(
                software=snapshot.software.name, version=snapshot.version
            )
        # General information about device
        self['DHID'] = self.placeholder.device.dhid
        self['DocumentID'] = self.document_id
        self['Public Link'] = '{url}{id}'.format(
            url=url_for('Device.main', _external=True), id=device.dhid
        )
        self['Lots'] = ', '.join([x.name for x in self.device.lots])
        for i, tag in zip(range(1, 3), device.tags):
            self['Tag {} Type'.format(i)] = 'unamed' if tag.provider else 'named'
            self['Tag {} ID'.format(i)] = tag.id
            self['Tag {} Organization'.format(i)] = tag.org.name

        self['Device Hardware ID'] = device.hid
        self['Device Type'] = device.t
        if isinstance(device, d.Computer) and not device.placeholder:
            self['Device Chassis'] = device.chassis.name
        self['Device Serial Number'] = none2str(device.serial_number)
        self['Device Model'] = none2str(device.model)
        self['Device Manufacturer'] = none2str(device.manufacturer)
        self['Registered in'] = format(device.created, '%c')
        self['Registered (process)'] = software
        self['Updated in (software)'] = device.updated

        if device.physical_status:
            self['Physical state'] = device.physical_status.type

        if device.allocated_status:
            self['Allocate state'] = device.allocated_status.type

        try:
            self['Lifecycle state'] = device.last_action_of(*states.Status.actions()).t
        except LookupError:
            pass

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

        benchram = get_action(device, 'BenchmarkRamSysbench')
        if benchram:
            self['Benchmark RamSysbench (points)'] = none2str(benchram.rate)

        self.get_placeholder_datas()

    def components(self):
        """Function to get all components information of a device."""
        assert isinstance(self.device, d.Computer)
        for ctype in self.ORDER_COMPONENTS:  # ctype: str
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
        if component:
            self['{} {} Manufacturer'.format(ctype, i)] = none2str(
                component.manufacturer
            )
            self['{} {} Model'.format(ctype, i)] = none2str(component.model)
            self['{} {} Serial Number'.format(ctype, i)] = none2str(
                component.serial_number
            )

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
            return

        self['{} {} Number of cores'.format(ctype, i)] = none2str(component.cores)
        self['{} {} Speed (GHz)'.format(ctype, i)] = none2str(component.speed)

        benchmark = get_action(component, 'BenchmarkProcessor')
        if benchmark:
            self['Benchmark {} {} (points)'.format(ctype, i)] = benchmark.rate

        sysbench = get_action(component, 'BenchmarkProcessorSysbench')
        if sysbench:
            self[
                'Benchmark ProcessorSysbench {} {} (points)'.format(ctype, i)
            ] = sysbench.rate

    def get_ram(self, ctype, i, component):
        """Particular fields for component Ram Module."""
        if component is None:
            return

        self['{} {} Size (MB)'.format(ctype, i)] = none2str(component.size)
        self['{} {} Speed (MHz)'.format(ctype, i)] = none2str(component.speed)

    def get_datastorage(self, ctype, i, component):
        """Particular fields for component DataStorage.
        A DataStorage can be HardDrive or SolidStateDrive.
        """

        if component is None:
            return

        snapshot = get_action(component, 'Snapshot')
        if snapshot:
            software = "{software} {version}".format(
                software=snapshot.software.name, version=snapshot.version
            )

        self['{} {} Size (MB)'.format(ctype, i)] = none2str(component.size)

        component_actions = sorted(component.actions, key=lambda x: x.created)
        erasures = [
            a
            for a in component_actions
            if a.type in ['EraseBasic', 'EraseSectors', 'DataWipe']
        ]
        erasure = erasures[-1] if erasures else None
        if not erasure:
            self['Erasure {} {}'.format(ctype, i)] = none2str(component.hid)
            serial_number = none2str(component.serial_number)
            self['Erasure {} {} Serial Number'.format(ctype, i)] = serial_number
            self['Erasure {} {} Size (MB)'.format(ctype, i)] = none2str(component.size)
        elif hasattr(erasure, 'type') and erasure.type == 'DataWipe':
            self['Erasure {} {}'.format(ctype, i)] = none2str(component.hid)
            serial_number = none2str(component.serial_number)
            self['Erasure {} {} Serial Number'.format(ctype, i)] = serial_number
            self['Erasure {} {} Size (MB)'.format(ctype, i)] = none2str(component.size)
            self['Erasure {} {} Software'.format(ctype, i)] = erasure.document.software
            self['Erasure {} {} Result'.format(ctype, i)] = get_result(erasure)
            self['Erasure {} {} Certificate URL'.format(ctype, i)] = (
                erasure.document.url and erasure.document.url.to_text() or ''
            )
        else:
            self['Erasure {} {}'.format(ctype, i)] = none2str(component.hid)
            serial_number = none2str(component.serial_number)
            self['Erasure {} {} Serial Number'.format(ctype, i)] = serial_number
            self['Erasure {} {} Size (MB)'.format(ctype, i)] = none2str(component.size)
            self['Erasure {} {} Software'.format(ctype, i)] = software

            result = get_result(erasure)
            self['Erasure {} {} Result'.format(ctype, i)] = result
            self['Erasure {} {} Type'.format(ctype, i)] = erasure.type
            self['Erasure {} {} Method'.format(ctype, i)] = erasure.method
            self['Erasure {} {} Elapsed (hours)'.format(ctype, i)] = format(
                erasure.elapsed
            )
            self['Erasure {} {} Date'.format(ctype, i)] = format(erasure.created)
            steps = ','.join((format(x) for x in erasure.steps))
            self['Erasure {} {} Steps'.format(ctype, i)] = steps
            steps_start_time = ','.join((format(x.start_time) for x in erasure.steps))
            self['Erasure {} {} Steps Start Time'.format(ctype, i)] = steps_start_time
            steps_end_time = ','.join((format(x.end_time) for x in erasure.steps))
            self['Erasure {} {} Steps End Time'.format(ctype, i)] = steps_end_time

        benchmark = get_action(component, 'BenchmarkDataStorage')
        if benchmark:
            self['Benchmark {} {} Read Speed (MB/s)'.format(ctype, i)] = none2str(
                benchmark.read_speed
            )
            self['Benchmark {} {} Writing speed (MB/s)'.format(ctype, i)] = none2str(
                benchmark.write_speed
            )

        test_storage = get_action(component, 'TestDataStorage')
        if not test_storage:
            return

        self['Test {} {} Software'.format(ctype, i)] = software
        self['Test {} {} Type'.format(ctype, i)] = test_storage.length.value
        self['Test {} {} Result'.format(ctype, i)] = get_result(test_storage)
        self['Test {} {} Power cycle count'.format(ctype, i)] = none2str(
            test_storage.power_cycle_count
        )
        self['Test {} {} Lifetime (days)'.format(ctype, i)] = none2str(
            test_storage.lifetime
        )
        self['Test {} {} Power on hours'.format(ctype, i)] = none2str(
            test_storage.power_on_hours
        )

    def get_graphic_card(self, ctype, i, component):
        """Particular fields for component GraphicCard."""
        if component:
            self['{} {} Memory (MB)'.format(ctype, i)] = none2str(component.memory)

    def get_placeholder_datas(self):
        # Placeholder
        self['PHID'] = none2str(self.placeholder.phid)
        self['Is Abstract'] = none2str(self.device.is_abstract())
        self['Pallet'] = none2str(self.placeholder.pallet)
        self['id Supplier'] = none2str(self.placeholder.id_device_supplier)
        self['Real Info'] = none2str(self.placeholder.info)
        self['Real Components'] = none2str(self.placeholder.components)
        self['Real Type'] = none2str(self.placeholder.device.type)
        self['Real Manufacturer'] = none2str(self.placeholder.device.manufacturer)
        self['Real Model'] = none2str(self.placeholder.device.model)
        self['Real Part Number'] = none2str(self.placeholder.device.part_number)
        self['Real Serial Number'] = none2str(self.placeholder.device.serial_number)


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
        self['Physical state'] = ''
        if device.physical_status:
            self['Physical state'] = device.physical_status.type

        self['Allocate state'] = ''
        if device.allocated_status:
            self['Allocate state'] = device.allocated_status.type

        try:
            self['Lifecycle state'] = device.last_action_of(*states.Trading.actions()).t
        except LookupError:
            self['Lifecycle state'] = ''
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


def get_result(erasure):
    """For the csv is necessary simplify the message of results"""
    if hasattr(erasure, 'type') and erasure.type == 'DataWipe':
        if erasure.document.success:
            return 'Success'
        return 'Failure'

    type_of_results = {
        Severity.Error: 'Failure',
        Severity.Warning: 'Success with Warnings',
        Severity.Notice: 'Success',
        Severity.Info: 'Success',
    }
    return type_of_results[erasure.severity]


def none2str(string):
    """convert none to empty str"""
    if string is None:
        return ''
    return format(string)


def get_action(component, action):
    """Filter one action from a component or return None"""
    result = [a for a in component.actions if a.type == action]
    return result[-1] if result else None


class ActionRow(OrderedDict):
    def __init__(self, allocate):
        super().__init__()
        # General information about allocates, deallocate and lives
        self['DHID'] = allocate['devicehubID']
        self['Hid'] = allocate['hid']
        self['Document-Name'] = allocate['document_name']
        self['Action-Type'] = allocate['action_type']
        self['Action-User-LastOwner-Supplier'] = allocate['trade_supplier']
        self['Action-User-LastOwner-Receiver'] = allocate['trade_receiver']
        self['Action-Create-By'] = allocate['action_create_by']
        self['Trade-Confirmed'] = allocate['trade_confirmed']
        self['Status-Created-By-Supplier-About-Reciber'] = allocate['status_supplier']
        self['Status-Receiver'] = allocate['status_receiver']
        self['Status Supplier – Created Date'] = allocate['status_supplier_created']
        self['Status Receiver – Created Date'] = allocate['status_receiver_created']
        self['Trade-Weight'] = allocate['trade_weight']
        self['Action-Create'] = allocate['created']
        self['Allocate-Start'] = allocate['start']
        self['Allocate-User-Code'] = allocate['finalUserCode']
        self['Allocate-NumUsers'] = allocate['numEndUsers']
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
            self.is_snapshot(self.is_deallocate(self.is_live(self.is_allocate(ac))))

    def is_allocate(self, ac):
        if ac.type == 'Allocate':
            self['Allocates'] += 1
        return ac

    def is_live(self, ac):
        if ac.type == 'Live':
            self['Lives'] += 1
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
            if not _ac.type == 'Snapshot':
                continue

            if _ac.created < ac.created:
                canary = True
                break

        if canary:
            self['Snapshot (Update)'] += 1
        else:
            self['Snapshot (Registers)'] += 1

    def quarter(self, month):
        q = {
            1: 'Q1',
            2: 'Q1',
            3: 'Q1',
            4: 'Q2',
            5: 'Q2',
            6: 'Q2',
            7: 'Q3',
            8: 'Q3',
            9: 'Q3',
            10: 'Q4',
            11: 'Q4',
            12: 'Q4',
        }
        return q[int(month)]
