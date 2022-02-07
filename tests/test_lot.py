import pytest
from flask import g
from pytest import raises
from json.decoder import JSONDecodeError

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.device.models import Desktop, Device, GraphicCard
from ereuse_devicehub.resources.enums import ComputerChassis
from ereuse_devicehub.resources.lot.models import Lot, LotDevice
from tests import conftest

"""In case of error, debug with:

    try:
        with db.session.begin_nested():

    except Exception as e:
        db.session.commit()
        print(e)
        a=1

"""


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_lot_model_children():
    """Tests the property Lot.children

    l1
    |
    l2
    |
    l3
    """
    lots = Lot('1'), Lot('2'), Lot('3')
    l1, l2, l3 = lots
    db.session.add_all(lots)
    db.session.flush()
    assert not l1.children
    assert not l1.parents
    assert not l2.children
    assert not l2.parents
    assert not l3.parents
    assert not l3.children

    l1.add_children(l2)
    assert l1.children == {l2}
    assert l2.parents == {l1}

    l2.add_children(l3)
    assert l1.children == {l2}
    assert l2.parents == {l1}
    assert l2.children == {l3}
    assert l3.parents == {l2}

    l2.delete()
    db.session.flush()
    assert not l1.children
    assert not l3.parents

    l1.delete()
    db.session.flush()
    l3b = Lot.query.one()
    assert l3 == l3b
    assert not l3.parents


@pytest.mark.mvp
def test_lot_modify_patch_endpoint_and_delete(user: UserClient):
    """Creates and modifies lot properties through the endpoint."""
    l, _ = user.post({'name': 'foo', 'description': 'baz'}, res=Lot)
    assert l['name'] == 'foo'
    assert l['description'] == 'baz'
    user.patch({'name': 'bar', 'description': 'bax'}, res=Lot, item=l['id'], status=204)
    l_after, _ = user.get(res=Lot, item=l['id'])
    assert l_after['name'] == 'bar'
    assert l_after['description'] == 'bax'
    user.patch({'description': 'bax'}, res=Lot, item=l['id'], status=204)
    user.delete(res=Lot, item=l['id'], status=204)
    user.get(res=Lot, item=l['id'], status=404)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_lot_device_relationship():
    device = Desktop(serial_number='foo',
                     model='bar',
                     manufacturer='foobar',
                     chassis=ComputerChassis.Lunchbox)
    device.components.add(GraphicCard(serial_number='foo', model='bar1', manufacturer='baz'))
    child = Lot('child')
    child.devices.add(device)
    db.session.add(child)
    db.session.flush()

    lot_device = LotDevice.query.one()  # type: LotDevice
    assert lot_device.device_id == device.id
    assert lot_device.lot_id == child.id
    assert lot_device.created
    assert lot_device.author_id == g.user.id
    assert device.lots == {child}
    assert device in child
    assert device in child.all_devices

    graphic = GraphicCard(serial_number='foo', model='bar')
    device.components.add(graphic)
    db.session.flush()
    assert graphic in child

    parent = Lot('parent')
    db.session.add(parent)
    db.session.flush()
    parent.add_children(child)
    assert child in parent


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_add_edge():
    """Tests creating an edge between child - parent - grandparent."""
    child = Lot('child')
    parent = Lot('parent')
    db.session.add(child)
    db.session.add(parent)
    db.session.flush()

    parent.add_children(child)

    assert child in parent
    assert len(child.paths) == 1
    assert len(parent.paths) == 1

    parent.remove_children(child)
    assert child not in parent
    assert len(child.paths) == 1
    assert len(parent.paths) == 1

    grandparent = Lot('grandparent')
    db.session.add(grandparent)
    db.session.flush()

    grandparent.add_children(parent)
    parent.add_children(child)

    assert parent in grandparent
    assert child in parent
    assert child in grandparent


def test_lot_multiple_parents(auth_app_context):
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

    grandparent1.add_children(parent)
    assert parent in grandparent1
    parent.add_children(child)
    assert child in parent
    assert child in grandparent1
    grandparent2.add_children(parent)
    assert parent in grandparent1
    assert parent in grandparent2
    assert child in parent
    assert child in grandparent1
    assert child in grandparent2

    p = parent.id
    c = child.id
    gp1 = grandparent1.id
    gp2 = grandparent2.id

    nodes = auth_app_context.resources[Lot.t].VIEW.ui_tree()
    assert nodes[0]['id'] == gp1
    assert nodes[0]['nodes'][0]['id'] == p
    assert nodes[0]['nodes'][0]['nodes'][0]['id'] == c
    assert nodes[0]['nodes'][0]['nodes'][0]['nodes'] == []
    assert nodes[1]['id'] == gp2
    assert nodes[1]['nodes'][0]['id'] == p
    assert nodes[1]['nodes'][0]['nodes'][0]['id'] == c
    assert nodes[1]['nodes'][0]['nodes'][0]['nodes'] == []

    # Now remove all childs

    grandparent1.remove_children(parent)
    assert parent not in grandparent1
    assert child in parent
    assert parent in grandparent2
    assert child not in grandparent1
    assert child in grandparent2

    nodes = auth_app_context.resources[Lot.t].VIEW.ui_tree()
    assert nodes[0]['id'] == gp1
    assert nodes[0]['nodes'] == []
    assert nodes[1]['id'] == gp2
    assert nodes[1]['nodes'][0]['id'] == p
    assert nodes[1]['nodes'][0]['nodes'][0]['id'] == c
    assert nodes[1]['nodes'][0]['nodes'][0]['nodes'] == []

    grandparent2.remove_children(parent)
    assert parent not in grandparent2
    assert parent not in grandparent1
    assert child not in grandparent2
    assert child not in grandparent1
    assert child in parent

    nodes = auth_app_context.resources[Lot.t].VIEW.ui_tree()
    assert nodes[0]['id'] == gp1
    assert nodes[0]['nodes'] == []
    assert nodes[1]['id'] == gp2
    assert nodes[1]['nodes'] == []
    assert nodes[2]['id'] == p
    assert nodes[2]['nodes'][0]['id'] == c
    assert nodes[2]['nodes'][0]['nodes'] == []

    parent.remove_children(child)
    assert child not in parent
    assert len(child.paths) == 1
    assert len(parent.paths) == 1

    nodes = auth_app_context.resources[Lot.t].VIEW.ui_tree()
    assert nodes[0]['id'] == gp1
    assert nodes[0]['nodes'] == []
    assert nodes[1]['id'] == gp2
    assert nodes[1]['nodes'] == []
    assert nodes[2]['id'] == p
    assert nodes[2]['nodes'] == []
    assert nodes[3]['id'] == c
    assert nodes[3]['nodes'] == []


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_lot_unite_graphs_and_find():
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

    l1.add_children(l2)
    assert l2 in l1
    l3.add_children(l2)
    assert l2 in l3
    l5.add_children(l7)
    assert l7 in l5
    l4.add_children(l5)
    assert l5 in l4
    assert l7 in l4
    l5.add_children(l8)
    assert l8 in l5
    l4.add_children(l6)
    assert l6 in l4
    l6.add_children(l5)
    assert l5 in l6 and l5 in l4

    # We unite the two graphs
    l2.add_children(l4)
    assert l4 in l2 and l5 in l2 and l6 in l2 and l7 in l2 and l8 in l2
    assert l4 in l3 and l5 in l3 and l6 in l3 and l7 in l3 and l8 in l3

    # We remove the union
    l2.remove_children(l4)
    assert l4 not in l2 and l5 not in l2 and l6 not in l2 and l7 not in l2 and l8 not in l2
    assert l4 not in l3 and l5 not in l3 and l6 not in l3 and l7 not in l3 and l8 not in l3


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_lot_roots():
    """Tests getting the method Lot.roots."""
    lots = Lot('1'), Lot('2'), Lot('3')
    l1, l2, l3 = lots
    db.session.add_all(lots)
    db.session.flush()

    assert set(Lot.roots()) == {l1, l2, l3}
    l1.add_children(l2)
    assert set(Lot.roots()) == {l1, l3}


@pytest.mark.mvp
def test_post_get_lot(user: UserClient):
    """Tests submitting and retreiving a basic lot."""
    l, _ = user.post({'name': 'Foo'}, res=Lot)
    assert l['name'] == 'Foo'
    l, _ = user.get(res=Lot, item=l['id'])
    assert l['name'] == 'Foo'


def test_lot_post_add_children_view_ui_tree_normal(user: UserClient):
    """Tests adding children lots to a lot through the view and
    GETting the results.
    """
    parent, _ = user.post(({'name': 'Parent'}), res=Lot)
    child, _ = user.post(({'name': 'Child'}), res=Lot)
    parent, _ = user.post({},
                          res=Lot,
                          item='{}/children'.format(parent['id']),
                          query=[('id', child['id'])])
    assert parent['children'][0]['id'] == child['id']
    child, _ = user.get(res=Lot, item=child['id'])
    assert child['parents'][0]['id'] == parent['id']

    # Format UiTree
    r = user.get(res=Lot, query=[('format', 'UiTree')])[0]
    lots, nodes = r['items'], r['tree']
    assert 1 == len(nodes)
    assert nodes[0]['id'] == parent['id']
    assert len(nodes[0]['nodes']) == 1
    assert nodes[0]['nodes'][0]['id'] == child['id']
    assert 2 == len(lots)
    assert 'Parent' == lots[parent['id']]['name']
    assert 'Child' == lots[child['id']]['name']
    assert lots[child['id']]['parents'][0]['name'] == 'Parent'

    # Normal list format
    lots = user.get(res=Lot)[0]['items']
    assert 2 == len(lots)
    assert lots[0]['name'] == 'Parent'
    assert lots[1]['name'] == 'Child'

    # List format with a filter
    lots = user.get(res=Lot, query=[('search', 'pa')])[0]['items']
    assert 1 == len(lots)
    assert lots[0]['name'] == 'Parent'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_lot_post_add_remove_device_view(user: UserClient):
    """Tests adding a device to a lot using POST and
    removing it with DELETE.
    """
    # todo check with components
    g.user = User.query.one()
    device = Desktop(serial_number='foo',
                     model='bar',
                     manufacturer='foobar',
                     chassis=ComputerChassis.Lunchbox,
                     owner_id=user.user['id'])
    db.session.add(device)
    db.session.commit()
    device_id = device.id
    devicehub_id = device.devicehub_id
    parent, _ = user.post(({'name': 'lot'}), res=Lot)
    lot, _ = user.post({},
                       res=Lot,
                       item='{}/devices'.format(parent['id']),
                       query=[('id', device_id)])
    lot = Lot.query.filter_by(id=lot['id']).one()
    assert list(lot.devices)[0].id == device_id, 'Lot contains device'
    device = Device.query.filter_by(devicehub_id=devicehub_id).one()
    assert len(device.lots) == 1
    # assert device['lots'][0]['id'] == lot['id'], 'Device is inside lot'
    assert list(device.lots)[0].id == lot.id, 'Device is inside lot'

    # Remove the device
    user.delete(res=Lot,
                item='{}/devices'.format(parent['id']),
                query=[('id', device_id)],
                status=200)
    assert not len(lot.devices)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_lot_error_add_device_from_other_user(user: UserClient):
    # TODO
    """Tests adding a device to a lot using POST and
    removing it with DELETE.
    """
    g.user = User.query.one()
    user2 = User(email='baz@baz.cxm', password='baz')
    user2.individuals.add(Person(name='Tommy'))
    db.session.add(user2)
    db.session.commit()

    device = Desktop(serial_number='foo',
                     model='bar',
                     manufacturer='foobar',
                     chassis=ComputerChassis.Lunchbox,
                     owner_id=user2.id)
    db.session.add(device)
    db.session.commit()

    device_id = device.id
    parent, _ = user.post(({'name': 'lot'}), res=Lot)
    lot, _ = user.post({},
                       res=Lot,
                       item='{}/devices'.format(parent['id']),
                       query=[('id', device_id)])
    lot = Lot.query.filter_by(id=lot['id']).one()
    assert list(lot.devices) == [], 'Lot contains device'
    assert len(lot.devices) == 0


@pytest.mark.mvp
def test_get_multiple_lots(user: UserClient):
    """Tests submitting and retreiving multiple lots."""
    l, _ = user.post({'name': 'Lot1', 'description': 'comments1,lot1,testcomment,'}, res=Lot)
    l, _ = user.post({'name': 'Lot2', 'description': 'comments2,lot2,testcomment,'}, res=Lot)
    l, _ = user.post({'name': 'Lot3', 'description': 'comments3,lot3,testcomment,'}, res=Lot)

    l, _ = user.get(res=Lot)
    assert len(l) == 3
