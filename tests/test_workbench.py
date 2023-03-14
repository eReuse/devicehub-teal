"""Tests that emulates the behaviour of a WorkbenchServer."""
import json
import math
import pathlib

import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.resources.action import models as em
from ereuse_devicehub.resources.action.models import (
    BenchmarkProcessor,
    BenchmarkRamSysbench,
    RateComputer,
)
from ereuse_devicehub.resources.device.exceptions import NeedsId
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.tag.model import Tag
from tests import conftest
from tests.conftest import file, file_workbench, json_encode, yaml2json


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_workbench_server_condensed(user: UserClient):
    """As :def:`.test_workbench_server_phases` but all the actions
    condensed in only one big ``Snapshot`` file, as described
    in the docs.
    """
    s = yaml2json('workbench-server-1.snapshot')
    s['device']['actions'].append(yaml2json('workbench-server-2.stress-test'))
    s['components'][4]['actions'].extend(
        (yaml2json('workbench-server-3.erase'), yaml2json('workbench-server-4.install'))
    )
    s['components'][5]['actions'].append(yaml2json('workbench-server-3.erase'))
    # Create tags
    for t in s['device']['tags']:
        user.post({'id': t['id']}, res=Tag)

    snapshot, _ = user.post(res=em.Snapshot, data=json_encode(s))
    pc_id = snapshot['device']['id']
    cpu_id = snapshot['components'][3]['id']
    ssd_id = snapshot['components'][4]['id']
    hdd_id = snapshot['components'][5]['id']
    actions = snapshot['actions']
    assert {(action['type'], action['device']) for action in actions} == {
        ('BenchmarkProcessorSysbench', cpu_id),
        ('StressTest', pc_id),
        ('EraseSectors', ssd_id),
        ('BenchmarkRamSysbench', pc_id),
        ('BenchmarkProcessor', cpu_id),
        ('Install', ssd_id),
        ('EraseSectors', hdd_id),
        ('BenchmarkDataStorage', ssd_id),
        ('BenchmarkDataStorage', hdd_id),
        ('TestDataStorage', ssd_id),
    }
    assert snapshot['closed']
    assert snapshot['severity'] == 'Info'
    db_dev = Device.query.filter_by(id=snapshot['device']['id']).one()
    device, _ = user.get(res=Device, item=db_dev.devicehub_id)
    assert device['dataStorageSize'] == 1100
    assert device['chassis'] == 'Tower'
    assert device['hid'] == 'desktop-d1mr-d1ml-d1s'
    assert device['graphicCardModel'] == device['components'][0]['model'] == 'gc1-1ml'
    assert device['networkSpeeds'] == [1000, 58]
    assert device['processorModel'] == device['components'][3]['model'] == 'p1-1ml'
    assert device['ramSize'] == 2048, 'There are 3 RAM: 2 x 1024 and 1 None sizes'
    # TODO JN why haven't same order in actions on each execution?
    assert any(
        [
            ac['type'] in [BenchmarkProcessor.t, BenchmarkRamSysbench.t]
            for ac in device['actions']
        ]
    )
    assert 'tag1' not in [x['id'] for x in device['tags']]


@pytest.mark.xfail(reason='Functionality not yet developed.')
def test_workbench_server_phases(user: UserClient):
    """Tests the phases described in the docs section `Snapshots from
    Workbench <http://devicehub.ereuse.org/
    actions.html#snapshots-from-workbench>`_.
    """
    # 1. Snapshot with sync / rate / benchmarks / test data storage
    s = yaml2json('workbench-server-1.snapshot')
    snapshot, _ = user.post(res=em.Snapshot, data=json_encode(s))
    assert not snapshot['closed'], 'Snapshot must be waiting for the new actions'

    # 2. stress test
    st = yaml2json('workbench-server-2.stress-test')
    st['snapshot'] = snapshot['id']
    stress_test, _ = user.post(res=em.StressTest, data=st)

    # 3. erase
    ssd_id, hdd_id = snapshot['components'][4]['id'], snapshot['components'][5]['id']
    e = yaml2json('workbench-server-3.erase')
    e['snapshot'], e['device'] = snapshot['id'], ssd_id
    erase1, _ = user.post(res=em.EraseSectors, data=e)

    # 3 bis. a second erase
    e = yaml2json('workbench-server-3.erase')
    e['snapshot'], e['device'] = snapshot['id'], hdd_id
    erase2, _ = user.post(res=em.EraseSectors, data=e)

    # 4. Install
    i = yaml2json('workbench-server-4.install')
    i['snapshot'], i['device'] = snapshot['id'], ssd_id
    install, _ = user.post(res=em.Install, data=i)

    # Check actions have been appended in Snapshot and devices
    # and that Snapshot is closed
    snapshot, _ = user.get(res=em.Snapshot, item=snapshot['id'])
    actions = snapshot['actions']
    assert len(actions) == 9
    assert actions[0]['type'] == 'Rate'
    assert actions[0]['device'] == 1
    assert actions[0]['closed']
    assert actions[0]['type'] == 'RateComputer'
    assert actions[0]['device'] == 1
    assert actions[1]['type'] == 'BenchmarkProcessor'
    assert actions[1]['device'] == 5
    assert actions[2]['type'] == 'BenchmarkProcessorSysbench'
    assert actions[2]['device'] == 5
    assert actions[3]['type'] == 'BenchmarkDataStorage'
    assert actions[3]['device'] == 6
    assert actions[4]['type'] == 'TestDataStorage'
    assert actions[4]['device'] == 6
    assert actions[4]['type'] == 'BenchmarkDataStorage'
    assert actions[4]['device'] == 7
    assert actions[5]['type'] == 'StressTest'
    assert actions[5]['device'] == 1
    assert actions[6]['type'] == 'EraseSectors'
    assert actions[6]['device'] == 6
    assert actions[7]['type'] == 'EraseSectors'
    assert actions[7]['device'] == 7
    assert actions[8]['type'] == 'Install'
    assert actions[8]['device'] == 6
    assert snapshot['closed']
    assert snapshot['severity'] == 'Info'

    pc, _ = user.get(res=Device, item=snapshot['devicehubID'])
    assert len(pc['actions']) == 10  # todo shall I add child actions?


@pytest.mark.mvp
def test_real_hp_11(user: UserClient):
    s = file('real-hp.snapshot.11')
    snapshot, _ = user.post(res=em.Snapshot, data=s)
    pc = snapshot['device']
    assert pc['hid'] == 'desktop-hewlett-packard-hp_compaq_8100_elite_sff-czc0408yjg'
    assert pc['chassis'] == 'Tower'
    assert set(e['type'] for e in snapshot['actions']) == {
        'BenchmarkDataStorage',
        'BenchmarkProcessor',
        'BenchmarkProcessorSysbench',
        'TestDataStorage',
        'BenchmarkRamSysbench',
        'StressTest',
        'TestBios',
        'VisualTest',
    }

    assert len(list(e['type'] for e in snapshot['actions'])) == 8
    assert pc['networkSpeeds'] == [1000, None], 'Device has no WiFi'
    assert pc['processorModel'] == 'intel core i3 cpu 530 @ 2.93ghz'
    assert pc['ramSize'] == 8192
    assert pc['dataStorageSize'] == 305245
    # todo check rating


@pytest.mark.mvp
def test_real_toshiba_11(user: UserClient):
    s = file('real-toshiba.snapshot.11')
    snapshot, _ = user.post(res=em.Snapshot, data=s)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_snapshot_real_eee_1001pxd_with_rate(user: UserClient):
    """Checks the values of the device, components,
    actions and their relationships of a real pc.
    """
    s = file('real-eee-1001pxd.snapshot.11')
    snapshot, _ = user.post(res=em.Snapshot, data=s)
    dev = Device.query.filter_by(id=snapshot['device']['id']).one()
    pc, _ = user.get(res=Device, item=dev.devicehub_id)
    assert pc['type'] == 'Laptop'
    assert pc['chassis'] == 'Netbook'
    assert pc['model'] == '1001pxd'
    assert pc['serialNumber'] == 'b8oaas048286'
    assert pc['manufacturer'] == 'asustek computer inc.'
    assert pc['hid'] == 'laptop-asustek_computer_inc.-1001pxd-b8oaas048286'
    assert len(pc['tags']) == 0
    assert pc['networkSpeeds'] == [
        100,
        0,
    ], 'Although it has WiFi we do not know the speed'
    # assert pc['actions'][0]['appearanceRange'] == 'A'
    # assert pc['actions'][0]['functionalityRange'] == 'B'
    # TODO add appearance and functionality Range in device[rate]

    components = snapshot['components']
    wifi = components[0]
    assert (
        wifi['hid'] == 'networkadapter-qualcomm_atheros-'
        'ar9285_wireless_network_adapter-74:2f:68:8b:fd:c8'
    )
    assert wifi['serialNumber'] == '74:2f:68:8b:fd:c8'
    assert wifi['wireless']
    eth = components[1]
    assert (
        eth['hid'] == 'networkadapter-qualcomm_atheros-'
        'ar8152_v2.0_fast_ethernet-14:da:e9:42:f6:7c'
    )
    assert eth['speed'] == 100
    assert not eth['wireless']
    cpu = components[2]
    assert cpu['address'] == 64
    assert cpu['cores'] == 1
    assert cpu['threads'] == 1
    assert cpu['speed'] == 1.667
    assert 'hid' in cpu
    assert pc['processorModel'] == cpu['model'] == 'intel atom cpu n455 @ 1.66ghz'
    db_cpu = Device.query.filter_by(id=cpu['id']).one()
    cpu, _ = user.get(res=Device, item=db_cpu.devicehub_id)
    actions = cpu['actions']
    sysbench = next(e for e in actions if e['type'] == em.BenchmarkProcessorSysbench.t)
    assert sysbench['elapsed'] == 164
    assert math.isclose(sysbench['rate'], 164, rel_tol=0.001)
    assert sysbench['snapshot'] == snapshot['id']
    assert sysbench['device'] == cpu['id']
    assert sysbench['parent'] == pc['id']
    benchmark_cpu = next(e for e in actions if e['type'] == em.BenchmarkProcessor.t)
    assert math.isclose(benchmark_cpu['rate'], 6666, rel_tol=0.001)
    assert benchmark_cpu['elapsed'] == 0
    action_types = tuple(e['type'] for e in actions)
    assert em.BenchmarkRamSysbench.t in action_types
    assert em.StressTest.t in action_types
    assert em.Snapshot.t in action_types
    assert len(actions) == 6
    gpu = components[3]
    assert (
        gpu['model']
        == 'atom processor d4xx/d5xx/n4xx/n5xx integrated graphics controller'
    )
    assert gpu['manufacturer'] == 'intel corporation'
    assert gpu['memory'] == 256
    db_gpu = Device.query.filter_by(id=gpu['id']).one()
    gpu, _ = user.get(res=Device, item=db_gpu.devicehub_id)
    action_types = tuple(e['type'] for e in gpu['actions'])
    assert em.BenchmarkRamSysbench.t in action_types
    assert em.StressTest.t in action_types
    assert em.Snapshot.t in action_types
    assert len(action_types) == 4
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
    assert hdd['hid'] == 'harddrive-hitachi-hts54322-e2024242cv86hj'
    assert hdd['interface'] == 'ATA'
    assert hdd['size'] == 238475
    db_hdd = Device.query.filter_by(id=hdd['id']).one()
    hdd, _ = user.get(res=Device, item=db_hdd.devicehub_id)
    action_types = tuple(e['type'] for e in hdd['actions'])
    assert em.BenchmarkRamSysbench.t in action_types
    assert em.StressTest.t in action_types
    assert em.BenchmarkDataStorage.t in action_types
    assert em.TestDataStorage.t in action_types
    assert em.EraseBasic.t in action_types
    assert em.Snapshot.t in action_types
    assert len(action_types) == 7
    erase = next(e for e in hdd['actions'] if e['type'] == em.EraseBasic.t)
    assert erase['endTime']
    assert erase['startTime']
    assert erase['severity'] == 'Info'
    assert hdd['privacy']['type'] == 'EraseBasic'
    mother = components[8]
    assert mother['hid'] == 'motherboard-asustek_computer_inc.-1001pxd-eee0123456789'


@pytest.mark.mvp
def test_real_custom(user: UserClient):
    s = file('real-custom.snapshot.11')
    snapshot, _ = user.post(res=em.Snapshot, data=s, status=201)
    # todo insert with tag


@pytest.mark.mvp
def test_real_hp_quad_core(user: UserClient):
    s = file('real-hp-quad-core.snapshot.11')
    snapshot, _ = user.post(res=em.Snapshot, data=s)


@pytest.mark.mvp
def test_real_eee_1000h(user: UserClient):
    s = file('asus-eee-1000h.snapshot.11')
    snapshot, _ = user.post(res=em.Snapshot, data=s)


SNAPSHOTS_NEED_ID = {
    'core2.snapshot.json',
    'asus-all-series.snapshot.json',
    'all-series.snapshot.json',
    'nox.snapshot.json',
    'ecs-computers.snapshot.json',
    'custom.snapshot.json',
    'ecs-2.snapshot.json',
}
"""Snapshots that do not generate HID requiring a custom ID."""


@pytest.mark.mvp
@pytest.mark.parametrize(
    'file',
    (
        pytest.param(f, id=f.name)
        for f in pathlib.Path(__file__).parent.joinpath('workbench_files').iterdir()
    ),
)
def test_workbench_fixtures(file: pathlib.Path, user: UserClient):
    """Uploads the Snapshot files Workbench tests generate.

    Keep this files up to date with the Workbench version.
    """
    s = json.load(file.open())
    user.post(res=em.Snapshot, data=json_encode(s), status=201)


@pytest.mark.mvp
def test_workbench_asus_1001pxd_rate_low(user: UserClient):
    """Tests an Asus 1001pxd with a low rate."""
    s = file('asus-1001pxd.snapshot')
    snapshot, _ = user.post(res=em.Snapshot, data=s)


@pytest.mark.mvp
def test_david(user: UserClient):
    s = file('david.lshw.snapshot')
    snapshot, _ = user.post(res=em.Snapshot, data=s)


def test_eresueprice_computer_type(user: UserClient):
    s = file_workbench('computer-type.snapshot')
    snapshot, _ = user.post(res=em.Snapshot, data=s)


def test_workbench_encoded_snapshot(user: UserClient):
    s = file_workbench('encoded.snapshot')
    snapshot, _ = user.post(res=em.Snapshot, data=s)
