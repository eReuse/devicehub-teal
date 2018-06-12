import pytest
from sqlalchemy.sql.elements import BinaryExpression

from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.inventory import Filters, InventoryView
from teal.utils import compiled


@pytest.mark.usefixtures('app_context')
def test_inventory_filters():
    schema = Filters()
    q = schema.load({
        'type': ['Microtower', 'Laptop'],
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
    assert '(device.type = %(type_1)s OR device.type = %(type_2)s)' in s
    assert 'device.manufacturer ILIKE %(manufacturer_1)s' in s
    assert 'rate.rating BETWEEN %(rating_1)s AND %(rating_2)s' in s
    assert 'rate.appearance BETWEEN %(appearance_1)s AND %(appearance_2)s' in s
    assert '(tag.id ILIKE %(id_1)s OR tag.id ILIKE %(id_2)s)' in s
    assert params == {
        'type_1': 'Microtower',
        'rating_2': 6.0,
        'manufacturer_1': 'Dell%',
        'appearance_1': 2.0,
        'appearance_2': 4.0,
        'id_1': 'bcn-%',
        'rating_1': 3.0,
        'id_2': 'activa-02%',
        'type_2': 'Laptop'
    }


@pytest.mark.usefixtures('app_context')
def test_inventory_query():
    schema = InventoryView.FindArgs()
    args = schema.load({
        'where': {'type': ['Computer']}
    })
    assert isinstance(args['where'], BinaryExpression), '``where`` must be a SQLAlchemy query'
