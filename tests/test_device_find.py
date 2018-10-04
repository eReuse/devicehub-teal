import pytest
from teal.utils import compiled

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.models import Desktop, Device, Laptop, SolidStateDrive
from ereuse_devicehub.resources.device.views import Filters, Sorting
from ereuse_devicehub.resources.enums import ComputerChassis
from ereuse_devicehub.resources.event.models import Snapshot
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

        db.session.commit()


@pytest.mark.usefixtures(device_query_dummy.__name__)
def test_device_query_no_filters(user: UserClient):
    i, _ = user.get(res=Device)
    assert tuple(d['type'] for d in i['items']) == (
        'Desktop', 'Laptop', 'Desktop', 'SolidStateDrive'
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


def test_device_query(user: UserClient):
    """Checks result of inventory."""
    user.post(conftest.file('basic.snapshot'), res=Snapshot)
    i, _ = user.get(res=Device)
    pc = next(d for d in i['items'] if d['type'] == 'Desktop')
    assert len(pc['events']) == 4
    assert len(pc['components']) == 3
    assert not pc['tags']


@pytest.mark.xfail(reason='Functionality not yet developed.')
def test_device_lots_query(user: UserClient):
    pass


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
