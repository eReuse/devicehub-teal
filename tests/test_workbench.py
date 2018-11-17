"""
Tests that emulates the behaviour of a WorkbenchServer.
"""
import json
import pathlib

import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.resources.device.exceptions import NeedsId
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.event import models as em
from ereuse_devicehub.resources.tag.model import Tag
from tests.conftest import file


def test_workbench_server_condensed(user: UserClient):
    """
    As :def:`.test_workbench_server_phases` but all the events
    condensed in only one big ``Snapshot`` file, as described
    in the docs.
    """
    s = file('workbench-server-1.snapshot')
    del s['expectedEvents']
    s['device']['events'].append(file('workbench-server-2.stress-test'))
    s['components'][4]['events'].extend((
        file('workbench-server-3.erase'),
        file('workbench-server-4.install')
    ))
    s['components'][5]['events'].append(file('workbench-server-3.erase'))
    # Create tags
    for t in s['device']['tags']:
        user.post({'id': t['id']}, res=Tag)

    snapshot, _ = user.post(res=em.Snapshot, data=s)
    events = snapshot['events']
    assert {(event['type'], event['device']) for event in events} == {
        ('AggregateRate', 1),
        ('WorkbenchRate', 1),
        ('BenchmarkProcessorSysbench', 5),
        ('StressTest', 1),
        ('EraseSectors', 6),
        ('BenchmarkRamSysbench', 1),
        ('BenchmarkProcessor', 5),
        ('Install', 6),
        ('EraseSectors', 7),
        ('BenchmarkDataStorage', 6),
        ('BenchmarkDataStorage', 7),
        ('TestDataStorage', 6)
    }
    assert snapshot['closed']
    assert snapshot['severity'] == 'Info'
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert device['dataStorageSize'] == 1100
    assert device['chassis'] == 'Tower'
    assert device['hid'] == 'd1mr-d1s-d1ml'
    assert device['graphicCardModel'] == device['components'][0]['model'] == 'gc1-1ml'
    assert device['networkSpeeds'] == [1000, 58]
    assert device['processorModel'] == device['components'][3]['model'] == 'p1-1ml'
    assert device['ramSize'] == 2048, 'There are 3 RAM: 2 x 1024 and 1 None sizes'
    assert device['rate']['closed']
    assert device['rate']['severity'] == 'Info'
    assert device['rate']['rating'] == 0
    assert device['rate']['workbench']
    assert device['rate']['appearanceRange'] == 'A'
    assert device['rate']['functionalityRange'] == 'B'
    assert device['tags'][0]['id'] == 'tag1'


@pytest.mark.xfail(reason='Functionality not yet developed.')
def test_workbench_server_phases(user: UserClient):
    """
    Tests the phases described in the docs section `Snapshots from
    Workbench <http://devicehub.ereuse.org/
    events.html#snapshots-from-workbench>`_.
    """
    # 1. Snapshot with sync / rate / benchmarks / test data storage
    s = file('workbench-server-1.snapshot')
    snapshot, _ = user.post(res=em.Snapshot, data=s)
    assert not snapshot['closed'], 'Snapshot must be waiting for the new events'

    # 2. stress test
    st = file('workbench-server-2.stress-test')
    st['snapshot'] = snapshot['id']
    stress_test, _ = user.post(res=em.StressTest, data=st)

    # 3. erase
    ssd_id, hdd_id = snapshot['components'][4]['id'], snapshot['components'][5]['id']
    e = file('workbench-server-3.erase')
    e['snapshot'], e['device'] = snapshot['id'], ssd_id
    erase1, _ = user.post(res=em.EraseSectors, data=e)

    # 3 bis. a second erase
    e = file('workbench-server-3.erase')
    e['snapshot'], e['device'] = snapshot['id'], hdd_id
    erase2, _ = user.post(res=em.EraseSectors, data=e)

    # 4. Install
    i = file('workbench-server-4.install')
    i['snapshot'], i['device'] = snapshot['id'], ssd_id
    install, _ = user.post(res=em.Install, data=i)

    # Check events have been appended in Snapshot and devices
    # and that Snapshot is closed
    snapshot, _ = user.get(res=em.Snapshot, item=snapshot['id'])
    events = snapshot['events']
    assert len(events) == 9
    assert events[0]['type'] == 'Rate'
    assert events[0]['device'] == 1
    assert events[0]['closed']
    assert events[0]['type'] == 'WorkbenchRate'
    assert events[0]['device'] == 1
    assert events[1]['type'] == 'BenchmarkProcessor'
    assert events[1]['device'] == 5
    assert events[2]['type'] == 'BenchmarkProcessorSysbench'
    assert events[2]['device'] == 5
    assert events[3]['type'] == 'BenchmarkDataStorage'
    assert events[3]['device'] == 6
    assert events[4]['type'] == 'TestDataStorage'
    assert events[4]['device'] == 6
    assert events[4]['type'] == 'BenchmarkDataStorage'
    assert events[4]['device'] == 7
    assert events[5]['type'] == 'StressTest'
    assert events[5]['device'] == 1
    assert events[6]['type'] == 'EraseSectors'
    assert events[6]['device'] == 6
    assert events[7]['type'] == 'EraseSectors'
    assert events[7]['device'] == 7
    assert events[8]['type'] == 'Install'
    assert events[8]['device'] == 6
    assert snapshot['closed']
    assert snapshot['severity'] == 'Info'

    pc, _ = user.get(res=Device, item=snapshot['id'])
    assert len(pc['events']) == 10  # todo shall I add child events?


def test_real_hp_11(user: UserClient):
    s = file('real-hp.snapshot.11')
    snapshot, _ = user.post(res=em.Snapshot, data=s)
    pc = snapshot['device']
    assert pc['hid'] == 'hewlett-packard-czc0408yjg-hp_compaq_8100_elite_sff'
    assert pc['chassis'] == 'Tower'
    assert set(e['type'] for e in snapshot['events']) == {
        'EreusePrice',
        'AggregateRate',
        'WorkbenchRate',
        'BenchmarkDataStorage',
        'BenchmarkProcessor',
        'BenchmarkProcessorSysbench',
        'TestDataStorage',
        'BenchmarkRamSysbench',
        'StressTest'
    }
    assert len(list(e['type'] for e in snapshot['events'])) == 9
    assert pc['networkSpeeds'] == [1000, None], 'Device has no WiFi'
    assert pc['processorModel'] == 'intel core i3 cpu 530 @ 2.93ghz'
    assert pc['ramSize'] == 8192
    assert pc['dataStorageSize'] == 305245
    # todo check rating


def test_real_toshiba_11(user: UserClient):
    s = file('real-toshiba.snapshot.11')
    snapshot, _ = user.post(res=em.Snapshot, data=s)


@pytest.mark.xfail(reason='Wrong rates values')
def test_snapshot_real_eee_1001pxd(user: UserClient):
    """
    Checks the values of the device, components,
    events and their relationships of a real pc.
    """
    s = file('real-eee-1001pxd.snapshot.11')
    snapshot, _ = user.post(res=em.Snapshot, data=s)
    pc, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert pc['type'] == 'Laptop'
    assert pc['chassis'] == 'Netbook'
    assert pc['model'] == '1001pxd'
    assert pc['serialNumber'] == 'b8oaas048286'
    assert pc['manufacturer'] == 'asustek computer inc.'
    assert pc['hid'] == 'asustek_computer_inc-b8oaas048286-1001pxd'
    assert pc['tags'] == []
    assert pc['networkSpeeds'] == [100, 0], 'Although it has WiFi we do not know the speed'
    assert pc['rate']
    rate = pc['rate']
    assert rate['appearanceRange'] == 'B'
    assert rate['functionalityRange'] == 'A'
    assert rate['processorRange'] == 'VERY_LOW'
    assert rate['ramRange'] == 'VERY_LOW'
    assert rate['ratingRange'] == 'VERY_LOW'
    assert rate['ram'] == 1.53
    assert rate['data_storage'] == 3.76
    assert rate['type'] == 'AggregateRate'
    assert rate['biosRange'] == 'C'
    assert rate['appearance'] > 0
    assert rate['functionality'] > 0
    assert rate['rating'] > 0 and rate['rating'] != 1
    components = snapshot['components']
    wifi = components[0]
    assert wifi['hid'] == 'qualcomm_atheros-74_2f_68_8b_fd_c8-ar9285_wireless_network_adapter'
    assert wifi['serialNumber'] == '74:2f:68:8b:fd:c8'
    assert wifi['wireless']
    eth = components[1]
    assert eth['hid'] == 'qualcomm_atheros-14_da_e9_42_f6_7c-ar8152_v2_0_fast_ethernet'
    assert eth['speed'] == 100
    assert not eth['wireless']
    cpu = components[2]
    assert cpu['address'] == 64
    assert cpu['cores'] == 1
    assert cpu['threads'] == 1
    assert cpu['speed'] == 1.667
    assert 'hid' not in cpu
    assert pc['processorModel'] == cpu['model'] == 'intel atom cpu n455 @ 1.66ghz'
    cpu, _ = user.get(res=Device, item=cpu['id'])
    events = cpu['events']
    sysbench = next(e for e in events if e['type'] == em.BenchmarkProcessorSysbench.t)
    assert sysbench['elapsed'] == 164
    assert sysbench['rate'] == 164
    assert sysbench['snapshot'] == snapshot['id']
    assert sysbench['device'] == cpu['id']
    assert sysbench['parent'] == pc['id']
    benchmark_cpu = next(e for e in events if e['type'] == em.BenchmarkProcessor.t)
    assert benchmark_cpu['rate'] == 6666
    assert benchmark_cpu['elapsed'] == 0
    event_types = tuple(e['type'] for e in events)
    assert em.BenchmarkRamSysbench.t in event_types
    assert em.StressTest.t in event_types
    assert em.Snapshot.t in event_types
    assert len(events) == 7
    gpu = components[3]
    assert gpu['model'] == 'atom processor d4xx/d5xx/n4xx/n5xx integrated graphics controller'
    assert gpu['manufacturer'] == 'intel corporation'
    assert gpu['memory'] == 256
    gpu, _ = user.get(res=Device, item=gpu['id'])
    event_types = tuple(e['type'] for e in gpu['events'])
    assert em.BenchmarkRamSysbench.t in event_types
    assert em.StressTest.t in event_types
    assert em.Snapshot.t in event_types
    assert len(event_types) == 3
    sound = components[4]
    assert sound['model'] == 'nm10/ich7 family high definition audio controller'
    sound = components[5]
    assert sound['model'] == 'usb 2.0 uvc vga webcam'
    ram = components[6]
    assert ram['interface'] == 'DDR2'
    assert ram['speed'] == 667
    assert pc['ramSize'] == ram['size'] == 1024
    hdd = components[7]
    assert hdd['type'] == 'HardDrive'
    assert hdd['hid'] == 'hitachi-e2024242cv86hj-hts54322'
    assert hdd['interface'] == 'ATA'
    assert hdd['size'] == 238475
    hdd, _ = user.get(res=Device, item=hdd['id'])
    event_types = tuple(e['type'] for e in hdd['events'])
    assert em.BenchmarkRamSysbench.t in event_types
    assert em.StressTest.t in event_types
    assert em.BenchmarkDataStorage.t in event_types
    assert em.TestDataStorage.t in event_types
    assert em.EraseBasic.t in event_types
    assert em.Snapshot.t in event_types
    assert len(event_types) == 6
    erase = next(e for e in hdd['events'] if e['type'] == em.EraseBasic.t)
    assert erase['endTime']
    assert erase['startTime']
    assert erase['severity'] == 'Info'
    assert hdd['privacy'] == 'EraseBasic'
    mother = components[8]
    assert mother['hid'] == 'asustek_computer_inc-eee0123456789-1001pxd'


def test_real_custom(user: UserClient):
    s = file('real-custom.snapshot.11')
    snapshot, _ = user.post(res=em.Snapshot, data=s, status=NeedsId)
    # todo insert with tag


def test_real_hp_quad_core(user: UserClient):
    s = file('real-hp-quad-core.snapshot.11')
    snapshot, _ = user.post(res=em.Snapshot, data=s)


def test_real_eee_1000h(user: UserClient):
    s = file('asus-eee-1000h.snapshot.11')
    snapshot, _ = user.post(res=em.Snapshot, data=s)


@pytest.mark.xfail(reason='We do not have a snapshot file to use')
def test_real_full_with_workbench_rate(user: UserClient):
    pass


SNAPSHOTS_NEED_ID = {
    'box-xavier.snapshot.json',
    'custom.lshw.snapshot.json',
    'nox.lshw.snapshot.json',
    'core2.lshw.snapshot.json',
    'all-series.lshw.snapshot.json',
    'ecs-2.lshw.snapshot.json',
    'ecs-computers.lshw.snapshot.json',
    'asus-all-series.lshw.snapshot.json'
}
"""Snapshots that do not generate HID requiring a custom ID."""


@pytest.mark.parametrize('file',
                         pathlib.Path(__file__).parent.joinpath('workbench_files').iterdir())
def test_workbench_fixtures(file: pathlib.Path, user: UserClient):
    """Uploads the Snapshot files Workbench tests generate.

    Keep this files up to date with the Workbench version.
    """
    s = json.load(file.open())
    user.post(res=em.Snapshot,
              data=s,
              status=201 if file.name not in SNAPSHOTS_NEED_ID else NeedsId)


def test_workbench_asus_1001pxd_rate_low(user: UserClient):
    """Tests an Asus 1001pxd with a low rate."""
    s = file('asus-1001pxd.snapshot')
    snapshot, _ = user.post(res=em.Snapshot, data=s)


def test_david(user: UserClient):
    s = file('david.lshw.snapshot')
    snapshot, _ = user.post(res=em.Snapshot, data=s)
