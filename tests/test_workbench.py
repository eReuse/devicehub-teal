"""
Tests that emulates the behaviour of a WorkbenchServer.
"""
import pytest
from ereuse_devicehub.client import UserClient
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.event.models import EraseSectors, Install, Snapshot, \
    StressTest
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
    s['components'][5]['events'] = [file('workbench-server-3.erase')]
    # Create tags
    user.post(res=Tag, query=[('ids', t['id']) for t in s['device']['tags']], data={})
    snapshot, _ = user.post(res=Snapshot, data=s)
    events = snapshot['events']
    assert {(event['type'], event['device']) for event in events} == {
        # todo missing Rate event aggregating the rates
        ('WorkbenchRate', 1),
        ('BenchmarkProcessorSysbench', 5),
        ('StressTest', 1),
        ('EraseSectors', 6),
        ('BenchmarkRamSysbench', 1),
        ('BenchmarkProcessor', 5),
        ('Install', 6),
        ('EraseSectors', 7),
        ('BenchmarkDataStorage', 6),
        ('TestDataStorage', 6)
    }
    assert snapshot['closed']
    assert not snapshot['error']


@pytest.mark.xfail(reason='Functionality not yet developed.')
def test_workbench_server_phases(user: UserClient):
    """
    Tests the phases described in the docs section `Snapshots from
    Workbench <http://devicehub.ereuse.org/
    events.html#snapshots-from-workbench>`_.
    """
    # 1. Snapshot with sync / rate / benchmarks / test data storage
    s = file('workbench-server-1.snapshot')
    snapshot, _ = user.post(res=Snapshot, data=s)
    assert not snapshot['closed'], 'Snapshot must be waiting for the new events'

    # 2. stress test
    st = file('workbench-server-2.stress-test')
    st['snapshot'] = snapshot['id']
    stress_test, _ = user.post(res=StressTest, data=st)

    # 3. erase
    ssd_id, hdd_id = snapshot['components'][4]['id'], snapshot['components'][5]['id']
    e = file('workbench-server-3.erase')
    e['snapshot'], e['device'] = snapshot['id'], ssd_id
    erase1, _ = user.post(res=EraseSectors, data=e)

    # 3 bis. a second erase
    e = file('workbench-server-3.erase')
    e['snapshot'], e['device'] = snapshot['id'], hdd_id
    erase2, _ = user.post(res=EraseSectors, data=e)

    # 4. Install
    i = file('workbench-server-4.install')
    i['snapshot'], i['device'] = snapshot['id'], ssd_id
    install, _ = user.post(res=Install, data=i)

    # Check events have been appended in Snapshot and devices
    # and that Snapshot is closed
    snapshot, _ = user.get(res=Snapshot, item=snapshot['id'])
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
    assert not snapshot['error']

    pc, _ = user.get(res=Device, item=snapshot['id'])
    assert len(pc['events']) == 10  # todo shall I add child events?
