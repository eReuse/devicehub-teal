import uuid

import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.action.models import Snapshot
from ereuse_devicehub.resources.device.models import (
    Desktop,
    Device,
    GraphicCard,
    Laptop,
    Server,
    SolidStateDrive,
)
from ereuse_devicehub.resources.device.search import DeviceSearch
from ereuse_devicehub.resources.device.views import Filters, Sorting
from ereuse_devicehub.resources.enums import ComputerChassis
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.teal.utils import compiled
from tests import conftest
from tests.conftest import file, json_encode, yaml2json


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_device_filters():
    schema = Filters()
    q = schema.load(
        {
            'type': ['Computer', 'Laptop'],
            'manufacturer': 'Dell',
            'rating': {'rating': [3, 6], 'appearance': [2, 4]},
            'tag': {'id': ['bcn-', 'activa-02']},
        }
    )
    s, params = compiled(Device, q)
    # Order between query clauses can change
    assert (
        '(device.type IN (%(type_1)s, %(type_2)s, %(type_3)s, %(type_4)s) '
        'OR device.type IN (%(type_5)s))' in s
    )
    assert 'device.manufacturer ILIKE %(manufacturer_1)s' in s
    assert 'rate.rating BETWEEN %(rating_1)s AND %(rating_2)s' in s
    assert 'rate.appearance BETWEEN %(appearance_1)s AND %(appearance_2)s' in s
    assert '(tag.id ILIKE %(id_1)s OR tag.id ILIKE %(id_2)s)' in s

    # type_x can be assigned at different values
    # ex: type_1 can be 'Desktop' in one execution but the next one 'Laptop'
    assert set(params.keys()) == {
        'id_2',
        'appearance_1',
        'type_1',
        'type_4',
        'rating_2',
        'type_5',
        'type_3',
        'type_2',
        'appearance_2',
        'id_1',
        'rating_1',
        'manufacturer_1',
    }
    assert set(params.values()) == {
        2.0,
        'Laptop',
        4.0,
        3.0,
        6.0,
        'Desktop',
        'activa-02%',
        'Server',
        'Dell%',
        'Computer',
        'bcn-%',
    }


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_device_sort():
    schema = Sorting()
    r = next(schema.load({'created': True}))
    assert str(r) == 'device.created ASC'


@pytest.fixture()
def device_query_dummy(app: Devicehub):
    """3 computers, where:

    1. s1 Desktop with a Processor
    2. s2 Desktop with an SSD
    3. s3 Laptop
    4. s4 Server with another SSD

    :param app:
    :return:
    """
    with app.app_context():
        devices = (  # The order matters ;-)
            Desktop(
                serial_number='1',
                model='ml1',
                manufacturer='mr1',
                chassis=ComputerChassis.Tower,
            ),
            Desktop(
                serial_number='2',
                model='ml2',
                manufacturer='mr2',
                chassis=ComputerChassis.Microtower,
            ),
            Laptop(
                serial_number='3',
                model='ml3',
                manufacturer='mr3',
                chassis=ComputerChassis.Detachable,
            ),
            Server(
                serial_number='4',
                model='ml4',
                manufacturer='mr4',
                chassis=ComputerChassis.Tower,
            ),
        )
        devices[0].components.add(
            GraphicCard(serial_number='1-gc', model='s1ml', manufacturer='s1mr')
        )
        devices[1].components.add(
            SolidStateDrive(serial_number='2-ssd', model='s2ml', manufacturer='s2mr')
        )
        devices[-1].components.add(
            SolidStateDrive(serial_number='4-ssd', model='s4ml', manufacturer='s4mr')
        )
        db.session.add_all(devices)
        db.session.commit()


@pytest.mark.usefixtures(device_query_dummy.__name__)
def test_device_query_no_filters(user: UserClient):
    i, _ = user.get(res=Device)
    assert ('1', '2', '3', '4', '1-gc', '2-ssd', '4-ssd') == tuple(
        d['serialNumber'] for d in i['items']
    )


@pytest.mark.usefixtures(device_query_dummy.__name__)
def test_device_query_filter_type(user: UserClient):
    i, _ = user.get(res=Device, query=[('filter', {'type': ['Desktop', 'Laptop']})])
    assert ('1', '2', '3') == tuple(d['serialNumber'] for d in i['items'])


@pytest.mark.usefixtures(device_query_dummy.__name__)
def test_device_query_filter_sort(user: UserClient):
    i, _ = user.get(
        res=Device,
        query=[
            ('sort', {'created': Sorting.DESCENDING}),
            ('filter', {'type': ['Computer']}),
        ],
    )
    assert ('4', '3', '2', '1') == tuple(d['serialNumber'] for d in i['items'])


@pytest.mark.usefixtures(device_query_dummy.__name__)
def test_device_query_filter_lots(user: UserClient):
    parent, _ = user.post({'name': 'Parent'}, res=Lot)
    child, _ = user.post({'name': 'Child'}, res=Lot)

    i, _ = user.get(res=Device, query=[('filter', {'lot': {'id': [parent['id']]}})])
    assert not i['items'], 'No devices in lot'

    parent, _ = user.post(
        {},
        res=Lot,
        item='{}/children'.format(parent['id']),
        query=[('id', child['id'])],
    )
    i, _ = user.get(res=Device, query=[('filter', {'type': ['Computer']})])
    assert ('1', '2', '3', '4') == tuple(d['serialNumber'] for d in i['items'])
    parent, _ = user.post(
        {},
        res=Lot,
        item='{}/devices'.format(parent['id']),
        query=[('id', d['id']) for d in i['items'][:2]],
    )
    child, _ = user.post(
        {},
        res=Lot,
        item='{}/devices'.format(child['id']),
        query=[('id', d['id']) for d in i['items'][2:]],
    )
    i, _ = user.get(res=Device, query=[('filter', {'lot': {'id': [parent['id']]}})])
    assert ('1', '2', '3', '4', '1-gc', '2-ssd', '4-ssd') == tuple(
        x['serialNumber'] for x in i['items']
    ), (
        'The parent lot contains 2 items plus indirectly the other '
        '2 from the child lot, with all their 2 components'
    )

    i, _ = user.get(
        res=Device,
        query=[
            ('filter', {'type': ['Computer'], 'lot': {'id': [parent['id']]}}),
        ],
    )
    assert ('1', '2', '3', '4') == tuple(x['serialNumber'] for x in i['items'])
    s, _ = user.get(res=Device, query=[('filter', {'lot': {'id': [child['id']]}})])
    assert ('3', '4', '4-ssd') == tuple(x['serialNumber'] for x in s['items'])
    s, _ = user.get(
        res=Device, query=[('filter', {'lot': {'id': [child['id'], parent['id']]}})]
    )
    assert ('1', '2', '3', '4', '1-gc', '2-ssd', '4-ssd') == tuple(
        x['serialNumber'] for x in s['items']
    ), 'Adding both lots is redundant in this case and we have the 4 elements.'


@pytest.mark.mvp
def test_device_query(user: UserClient):
    """Checks result of inventory."""
    snapshot, _ = user.post(conftest.file('basic.snapshot'), res=Snapshot)
    i, _ = user.get(res=Device)
    assert i['url'] == '/devices/'
    assert i['items'][0]['url'] == '/devices/%s' % snapshot['device']['devicehubID']
    pc = next(d for d in i['items'] if d['type'] == 'Desktop')
    assert len(pc['actions']) == 3
    assert len(pc['components']) == 3


@pytest.mark.mvp
def test_device_query_permitions(user: UserClient, user2: UserClient):
    """Checks result of inventory for two users"""
    user.post(file('basic.snapshot'), res=Snapshot)
    i, _ = user.get(res=Device)
    pc1 = next(d for d in i['items'] if d['type'] == 'Desktop')

    i2, _ = user2.get(res=Device)
    assert i2['items'] == []

    basic_snapshot = yaml2json('basic.snapshot')
    basic_snapshot['uuid'] = f"{uuid.uuid4()}"
    user2.post(json_encode(basic_snapshot), res=Snapshot)
    i2, _ = user2.get(res=Device)
    pc2 = next(d for d in i2['items'] if d['type'] == 'Desktop')

    assert pc1['id'] != pc2['id']
    assert pc1['hid'] == pc2['hid']


@pytest.mark.mvp
def test_device_search_all_devices_token_if_empty(app: Devicehub, user: UserClient):
    """Ensures DeviceSearch can regenerate itself when the table is empty."""
    user.post(file('basic.snapshot'), res=Snapshot)
    with app.app_context():
        app.db.session.execute('TRUNCATE TABLE {}'.format(DeviceSearch.__table__.name))
        app.db.session.commit()
    i, _ = user.get(res=Device, query=[('search', 'Desktop')])
    assert not len(i['items'])
    with app.app_context():
        DeviceSearch.set_all_devices_tokens_if_empty(app.db.session)
        app.db.session.commit()
    i, _ = user.get(res=Device, query=[('search', 'Desktop')])
    assert i['items']


@pytest.mark.mvp
def test_device_search_regenerate_table(app: DeviceSearch, user: UserClient):
    user.post(file('basic.snapshot'), res=Snapshot)
    i, _ = user.get(res=Device, query=[('search', 'Desktop')])
    assert i['items'], 'Normal search works'
    with app.app_context():
        app.db.session.execute('TRUNCATE TABLE {}'.format(DeviceSearch.__table__.name))
        app.db.session.commit()
    i, _ = user.get(res=Device, query=[('search', 'Desktop')])
    assert not i['items'], 'Truncate deleted all items'
    runner = app.test_cli_runner()
    runner.invoke('inv', 'search')
    i, _ = user.get(res=Device, query=[('search', 'Desktop')])
    assert i['items'], 'Regenerated re-made the table'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_device_query_search(user: UserClient):
    # todo improve
    snapshot, _ = user.post(file('basic.snapshot'), res=Snapshot)
    dev = Device.query.filter_by(id=snapshot['device']['id']).one()
    user.post(file('computer-monitor.snapshot'), res=Snapshot)
    user.post(file('real-eee-1001pxd.snapshot.11'), res=Snapshot)
    i, _ = user.get(res=Device, query=[('search', 'desktop')])
    assert i['items'][0]['id'] == dev.id
    i, _ = user.get(res=Device, query=[('search', 'intel')])
    assert len(i['items']) == 1
    dev1 = Device.query.filter_by(id=i['items'][0]['id']).one()
    i, _ = user.get(res=Device, query=[('search', dev1.devicehub_id)])
    assert len(i['items']) == 1
    dev2 = Device.query.filter_by(id=i['items'][0]['id']).one()
    i, _ = user.get(res=Device, query=[('search', dev2.devicehub_id)])
    assert len(i['items']) == 1


@pytest.mark.mvp
def test_device_query_search_synonyms_asus(user: UserClient):
    user.post(file('real-eee-1001pxd.snapshot.11'), res=Snapshot)
    i, _ = user.get(res=Device, query=[('search', 'asustek')])
    assert 1 == len(i['items'])
    i, _ = user.get(res=Device, query=[('search', 'asus')])
    assert 1 == len(i['items'])


@pytest.mark.mvp
def test_device_query_search_synonyms_intel(user: UserClient):
    s = yaml2json('real-hp.snapshot.11')
    s['device']['model'] = 'foo'  # The model had the word 'HP' in it
    user.post(json_encode(s), res=Snapshot)
    i, _ = user.get(res=Device, query=[('search', 'hewlett packard')])
    assert 1 == len(i['items'])
    i, _ = user.get(res=Device, query=[('search', 'hewlett')])
    assert 1 == len(i['items'])
    i, _ = user.get(res=Device, query=[('search', 'hp')])
    assert 1 == len(i['items'])
    i, _ = user.get(res=Device, query=[('search', 'h.p')])
    assert 1 == len(i['items'])
