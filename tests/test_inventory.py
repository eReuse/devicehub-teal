import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.models import Desktop, Device, Laptop, Microtower, \
    SolidStateDrive
from ereuse_devicehub.resources.inventory import Filters, Inventory, Sorting
from teal.utils import compiled


@pytest.mark.usefixtures('app_context')
def test_inventory_filters():
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
    assert '(device.type IN (%(type_1)s, %(type_2)s, %(type_3)s, %(type_4)s, ' \
           '%(type_5)s, %(type_6)s) OR device.type IN (%(type_7)s))' in s
    assert 'device.manufacturer ILIKE %(manufacturer_1)s' in s
    assert 'rate.rating BETWEEN %(rating_1)s AND %(rating_2)s' in s
    assert 'rate.appearance BETWEEN %(appearance_1)s AND %(appearance_2)s' in s
    assert '(tag.id ILIKE %(id_1)s OR tag.id ILIKE %(id_2)s)' in s

    # type_x can be assigned at different values
    # ex: type_1 can be 'Desktop' in one execution but the next one 'Laptop'
    assert set(params.keys()) == {
        'id_1',
        'manufacturer_1',
        'type_4',
        'type_3',
        'id_2',
        'type_1',
        'rating_1',
        'type_5',
        'appearance_2',
        'type_6',
        'type_7',
        'appearance_1',
        'rating_2',
        'type_2'
    }
    assert set(params.values()) == {
        'bcn-%',
        'Dell%',
        'Laptop',
        'Server',
        'activa-02%',
        'Computer',
        3.0,
        'Microtower',
        4.0,
        'Netbook',
        'Laptop',
        2.0,
        6.0,
        'Desktop'
    }


@pytest.mark.usefixtures('app_context')
def test_inventory_sort():
    schema = Sorting()
    r = next(schema.load({'created': True}))
    assert str(r) == 'device.created ASC'


@pytest.fixture()
def inventory_query_dummy(app: Devicehub):
    with app.app_context():
        db.session.add_all((  # The order matters ;-)
            Desktop(serial_number='s1', model='ml1', manufacturer='mr1'),
            Laptop(serial_number='s3', model='ml3', manufacturer='mr3'),
            Microtower(serial_number='s2', model='ml2', manufacturer='mr2'),
            SolidStateDrive(serial_number='s4', model='ml4', manufacturer='mr4')
        ))
        db.session.commit()


@pytest.mark.usefixtures('inventory_query_dummy')
def test_inventory_query_no_filters(user: UserClient):
    i, _ = user.get(res=Inventory)
    assert tuple(d['type'] for d in i['devices']) == (
        'SolidStateDrive', 'Microtower', 'Laptop', 'Desktop'
    )


@pytest.mark.usefixtures('inventory_query_dummy')
def test_inventory_query_filter_type(user: UserClient):
    i, _ = user.get(res=Inventory, query=[('filter', {'type': ['Computer', 'Microtower']})])
    assert tuple(d['type'] for d in i['devices']) == ('Microtower', 'Laptop', 'Desktop')


@pytest.mark.usefixtures('inventory_query_dummy')
def test_inventory_query_filter_sort(user: UserClient):
    i, _ = user.get(res=Inventory, query=[
        ('sort', {'created': Sorting.ASCENDING}),
        ('filter', {'type': ['Computer']})
    ])
    assert tuple(d['type'] for d in i['devices']) == ('Desktop', 'Laptop', 'Microtower')
