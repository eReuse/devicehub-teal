import pytest
from teal.utils import compiled

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.models import Desktop, Device, Laptop, Processor, \
    SolidStateDrive
from ereuse_devicehub.resources.device.search import DeviceSearch
from ereuse_devicehub.resources.device.views import Filters, Sorting
from ereuse_devicehub.resources.enums import ComputerChassis
from ereuse_devicehub.resources.event.models import Snapshot
from ereuse_devicehub.resources.lot.models import Lot
from tests import conftest
from tests.conftest import file


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_device_filters():
    schema = Filters()
    q = schema.load({
        'type': ['Computer', 'Laptop'],
        'manufacturer': 'Dell',
        'rating': {
            'rating': [3, 6],
            'appearance': [2, 4]
        },
        'tag': {
            'id': ['bcn-', 'activa-02']
        }
    })
    s, params = compiled(Device, q)
    # Order between query clauses can change
    assert '(device.type IN (%(type_1)s, %(type_2)s, %(type_3)s, %(type_4)s) ' \
           'OR device.type IN (%(type_5)s))' in s
    assert 'device.manufacturer ILIKE %(manufacturer_1)s' in s
    assert 'rate.rating BETWEEN %(rating_1)s AND %(rating_2)s' in s
    assert 'rate.appearance BETWEEN %(appearance_1)s AND %(appearance_2)s' in s
    assert '(tag.id ILIKE %(id_1)s OR tag.id ILIKE %(id_2)s)' in s

    # type_x can be assigned at different values
    # ex: type_1 can be 'Desktop' in one execution but the next one 'Laptop'
    assert set(params.keys()) == {'id_2', 'appearance_1', 'type_1', 'type_4', 'rating_2', 'type_5',
                                  'type_3', 'type_2', 'appearance_2', 'id_1', 'rating_1',
                                  'manufacturer_1'}
    assert set(params.values()) == {2.0, 'Laptop', 4.0, 3.0, 6.0, 'Desktop', 'activa-02%',
                                    'Server', 'Dell%', 'Computer', 'bcn-%'}


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_device_sort():
    schema = Sorting()
    r = next(schema.load({'created': True}))
    assert str(r) == 'device.created ASC'


@pytest.fixture()
def device_query_dummy(app: Devicehub):
    with app.app_context():
        devices = (  # The order matters ;-)
            Desktop(serial_number='s1',
                    model='ml1',
                    manufacturer='mr1',
                    chassis=ComputerChassis.Tower),
            Laptop(serial_number='s3',
                   model='ml3',
                   manufacturer='mr3',
                   chassis=ComputerChassis.Detachable),
            Desktop(serial_number='s2',
                    model='ml2',
                    manufacturer='mr2',
                    chassis=ComputerChassis.Microtower),
            SolidStateDrive(serial_number='s4', model='ml4', manufacturer='mr4')
        )
        devices[-1].parent = devices[0]  # s4 in s1
        db.session.add_all(devices)

        devices[0].components.add(Processor(model='ml5', manufacturer='mr5'))

        db.session.commit()


@pytest.mark.usefixtures(device_query_dummy.__name__)
def test_device_query_no_filters(user: UserClient):
    i, _ = user.get(res=Device)
    assert tuple(d['type'] for d in i['items']) == (
        'Desktop', 'Laptop', 'Desktop', 'SolidStateDrive', 'Processor'
    )


@pytest.mark.usefixtures(device_query_dummy.__name__)
def test_device_query_filter_type(user: UserClient):
    i, _ = user.get(res=Device, query=[('filter', {'type': ['Desktop', 'Laptop']})])
    assert tuple(d['type'] for d in i['items']) == ('Desktop', 'Laptop', 'Desktop')


@pytest.mark.usefixtures(device_query_dummy.__name__)
def test_device_query_filter_sort(user: UserClient):
    i, _ = user.get(res=Device, query=[
        ('sort', {'created': Sorting.ASCENDING}),
        ('filter', {'type': ['Computer']})
    ])
    assert tuple(d['type'] for d in i['items']) == ('Desktop', 'Laptop', 'Desktop')


@pytest.mark.usefixtures(device_query_dummy.__name__)
def test_device_query_filter_lots(user: UserClient):
    parent, _ = user.post({'name': 'Parent'}, res=Lot)
    child, _ = user.post({'name': 'Child'}, res=Lot)

    i, _ = user.get(res=Device, query=[
        ('filter', {'lot': {'id': [parent['id']]}})
    ])
    assert len(i['items']) == 0, 'No devices in lot'

    parent, _ = user.post({},
                          res=Lot,
                          item='{}/children'.format(parent['id']),
                          query=[('id', child['id'])])
    i, _ = user.get(res=Device, query=[
        ('filter', {'type': ['Computer']})
    ])
    lot, _ = user.post({},
                       res=Lot,
                       item='{}/devices'.format(parent['id']),
                       query=[('id', d['id']) for d in i['items'][:-1]])
    lot, _ = user.post({},
                       res=Lot,
                       item='{}/devices'.format(child['id']),
                       query=[('id', i['items'][-1]['id'])])
    i, _ = user.get(res=Device, query=[
        ('filter', {'lot': {'id': [parent['id']]}}),
        ('sort', {'id': Sorting.ASCENDING})
    ])
    assert tuple(x['id'] for x in i['items']) == (1, 2, 3, 4, 5), \
        'The parent lot contains 2 items plus indirectly the third one, and 1st device the HDD.'

    i, _ = user.get(res=Device, query=[
        ('filter', {'type': ['Computer'], 'lot': {'id': [parent['id']]}}),
        ('sort', {'id': Sorting.ASCENDING})
    ])
    assert tuple(x['id'] for x in i['items']) == (1, 2, 3)

    s, _ = user.get(res=Device, query=[
        ('filter', {'lot': {'id': [child['id']]}})
    ])
    assert len(s['items']) == 1
    assert s['items'][0]['chassis'] == 'Microtower', 'The child lot only contains the last device.'
    s, _ = user.get(res=Device, query=[
        ('filter', {'lot': {'id': [child['id'], parent['id']]}})
    ])
    assert all(x['id'] == id for x, id in zip(i['items'], (1, 2, 3, 4))), \
        'Adding both lots is redundant in this case and we have the 4 elements.'
    i, _ = user.get(res=Device, query=[
        ('filter', {'lot': {'id': [parent['id']]}, 'type': ['Computer']}),
        ('sort', {'id': Sorting.ASCENDING})
    ])
    assert tuple(x['id'] for x in i['items']) == (1, 2, 3), 'Only computers now'


def test_device_query(user: UserClient):
    """Checks result of inventory."""
    user.post(conftest.file('basic.snapshot'), res=Snapshot)
    i, _ = user.get(res=Device)
    assert i['url'] == '/devices/'
    assert i['items'][0]['url'] == '/devices/1'
    pc = next(d for d in i['items'] if d['type'] == 'Desktop')
    assert len(pc['events']) == 4
    assert len(pc['components']) == 3
    assert not pc['tags']


@pytest.mark.xfail(reason='Functionality not yet developed.')
def test_device_lots_query(user: UserClient):
    pass


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


def test_device_query_search(user: UserClient):
    # todo improve
    user.post(file('basic.snapshot'), res=Snapshot)
    user.post(file('computer-monitor.snapshot'), res=Snapshot)
    user.post(file('real-eee-1001pxd.snapshot.11'), res=Snapshot)
    i, _ = user.get(res=Device, query=[('search', 'desktop')])
    assert i['items'][0]['id'] == 1
    i, _ = user.get(res=Device, query=[('search', 'intel')])
    assert len(i['items']) == 1


@pytest.mark.xfail(reason='No dictionary yet that knows asustek = asus')
def test_device_query_search_synonyms_asus(user: UserClient):
    user.post(file('real-eee-1001pxd.snapshot.11'), res=Snapshot)
    i, _ = user.get(res=Device, query=[('search', 'asustek')])
    assert len(i['items']) == 1
    i, _ = user.get(res=Device, query=[('search', 'asus')])
    assert len(i['items']) == 1


@pytest.mark.xfail(reason='No dictionary yet that knows hp = hewlett packard')
def test_device_query_search_synonyms_intel(user: UserClient):
    s = file('real-hp.snapshot.11')
    s['device']['model'] = 'foo'  # The model had the word 'HP' in it
    user.post(s, res=Snapshot)
    i, _ = user.get(res=Device, query=[('search', 'hewlett packard')])
    assert len(i['items']) == 1
    i, _ = user.get(res=Device, query=[('search', 'hewlett')])
    assert len(i['items']) == 1
    i, _ = user.get(res=Device, query=[('search', 'hp')])
    assert len(i['items']) == 1
