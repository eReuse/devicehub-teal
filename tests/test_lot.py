import pytest
from flask import g

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.models import Desktop
from ereuse_devicehub.resources.enums import ComputerChassis
from ereuse_devicehub.resources.lot.models import Lot, LotDevice
from tests import conftest

"""
In case of error, debug with:

    try:
        with db.session.begin_nested():
            
    except Exception as e:
        db.session.commit()
        print(e)
        a=1

"""


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_lot_device_relationship():
    device = Desktop(serial_number='foo',
                     model='bar',
                     manufacturer='foobar',
                     chassis=ComputerChassis.Lunchbox)
    lot = Lot('lot1')
    lot.devices.add(device)
    db.session.add(lot)
    db.session.flush()

    lot_device = LotDevice.query.one()  # type: LotDevice
    assert lot_device.device_id == device.id
    assert lot_device.lot_id == lot.id
    assert lot_device.created
    assert lot_device.author_id == g.user.id
    assert device.lots == {lot}


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_add_edge():
    """Tests creating an edge between child - parent - grandparent."""
    child = Lot('child')
    parent = Lot('parent')
    db.session.add(child)
    db.session.add(parent)
    db.session.flush()

    parent.add_child(child)

    assert child in parent
    assert len(child.paths) == 1
    assert len(parent.paths) == 1

    parent.remove_child(child)
    assert child not in parent
    assert len(child.paths) == 1
    assert len(parent.paths) == 1

    grandparent = Lot('grandparent')
    db.session.add(grandparent)
    db.session.flush()

    grandparent.add_child(parent)
    parent.add_child(child)

    assert parent in grandparent
    assert child in parent
    assert child in grandparent


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_lot_multiple_parents():
    """Tests creating a lot with two parent lots:

    grandparent1 grandparent2
             \   /
            parent
              |
            child
    """
    lots = Lot('child'), Lot('parent'), Lot('grandparent1'), Lot('grandparent2')
    child, parent, grandparent1, grandparent2 = lots
    db.session.add_all(lots)
    db.session.flush()

    grandparent1.add_child(parent)
    assert parent in grandparent1
    parent.add_child(child)
    assert child in parent
    assert child in grandparent1
    grandparent2.add_child(parent)
    assert parent in grandparent1
    assert parent in grandparent2
    assert child in parent
    assert child in grandparent1
    assert child in grandparent2

    grandparent1.remove_child(parent)
    assert parent not in grandparent1
    assert child in parent
    assert parent in grandparent2
    assert child not in grandparent1
    assert child in grandparent2

    grandparent2.remove_child(parent)
    assert parent not in grandparent2
    assert parent not in grandparent1
    assert child not in grandparent2
    assert child not in grandparent1
    assert child in parent

    parent.remove_child(child)
    assert child not in parent
    assert len(child.paths) == 1
    assert len(parent.paths) == 1


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_lot_unite_graphs():
    """Adds and removes children uniting already existing graphs.

    1  3
     \/
     2

      4
     | \
     |  6
     \ /
      5
     | \
     7  8

     This builds the graph and then unites 2 - 4.
    """

    lots = tuple(Lot(str(i)) for i in range(1, 9))
    l1, l2, l3, l4, l5, l6, l7, l8 = lots
    db.session.add_all(lots)
    db.session.flush()

    l1.add_child(l2)
    assert l2 in l1
    l3.add_child(l2)
    assert l2 in l3
    l5.add_child(l7)
    assert l7 in l5
    l4.add_child(l5)
    assert l5 in l4
    assert l7 in l4
    l5.add_child(l8)
    assert l8 in l5
    l4.add_child(l6)
    assert l6 in l4
    l6.add_child(l5)
    assert l5 in l6 and l5 in l4

    # We unite the two graphs
    l2.add_child(l4)
    assert l4 in l2 and l5 in l2 and l6 in l2 and l7 in l2 and l8 in l2
    assert l4 in l3 and l5 in l3 and l6 in l3 and l7 in l3 and l8 in l3

    # We remove the union
    l2.remove_child(l4)
    assert l4 not in l2 and l5 not in l2 and l6 not in l2 and l7 not in l2 and l8 not in l2
    assert l4 not in l3 and l5 not in l3 and l6 not in l3 and l7 not in l3 and l8 not in l3


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_lot_roots():
    """Tests getting the method Lot.roots."""
    lots = Lot('1'), Lot('2'), Lot('3')
    l1, l2, l3 = lots
    db.session.add_all(lots)
    db.session.flush()

    assert set(Lot.roots()) == {l1, l2, l3}
    l1.add_child(l2)
    assert set(Lot.roots()) == {l1, l3}


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_lot_model_children():
    """Tests the property Lot.children"""
    lots = Lot('1'), Lot('2'), Lot('3')
    l1, l2, l3 = lots
    db.session.add_all(lots)
    db.session.flush()

    l1.add_child(l2)
    db.session.flush()

    children = l1.children
    assert list(children) == [l2]


def test_post_get_lot(user: UserClient):
    """Tests submitting and retreiving a basic lot."""
    l, _ = user.post({'name': 'Foo'}, res=Lot)
    assert l['name'] == 'Foo'
    l, _ = user.get(res=Lot, item=l['id'])
    assert l['name'] == 'Foo'
    assert not l['children']


def test_post_add_children_view(user: UserClient):
    """Tests adding children lots to a lot through the view."""
    parent, _ = user.post(({'name': 'Parent'}), res=Lot)
    child, _ = user.post(({'name': 'Child'}), res=Lot)
    parent, _ = user.post({},
                          res=Lot,
                          item='{}/children'.format(parent['id']),
                          query=[('id', child['id'])])
    assert parent['children'][0]['id'] == child['id']
    child, _ = user.get(res=Lot, item=child['id'])
    assert child['parents'][0]['id'] == parent['id']
    return child['id']


def test_lot_post_add_remove_device_view(app: Devicehub, user: UserClient):
    """Tests adding a device to a lot using POST and
    removing it with DELETE."""
    with app.app_context():
        device = Desktop(serial_number='foo',
                         model='bar',
                         manufacturer='foobar',
                         chassis=ComputerChassis.Lunchbox)
        db.session.add(device)
        db.session.commit()
        device_id = device.id
    parent, _ = user.post(({'name': 'lot'}), res=Lot)
    lot, _ = user.post({},
                       res=Lot,
                       item='{}/devices'.format(parent['id']),
                       query=[('id', device_id)])
    assert lot['devices'][0]['id'] == device_id
    # Remove the device
    lot, _ = user.delete(res=Lot,
                         item='{}/devices'.format(parent['id']),
                         query=[('id', device_id)],
                         status=200)
    assert not len(lot['devices'])
