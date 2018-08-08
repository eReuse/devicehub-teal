import pytest
from flask import g
from sqlalchemy_utils import Ltree

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Desktop
from ereuse_devicehub.resources.enums import ComputerChassis
from ereuse_devicehub.resources.lot.models import Edge, Lot, LotDevice
from tests import conftest


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_lot_device_relationship():
    device = Desktop(serial_number='foo',
                     model='bar',
                     manufacturer='foobar',
                     chassis=ComputerChassis.Lunchbox)
    lot = Lot(name='lot1')
    lot.devices.add(device)
    db.session.add(lot)
    db.session.flush()

    lot_device = LotDevice.query.one()  # type: LotDevice
    assert lot_device.device_id == device.id
    assert lot_device.lot_id == lot.id
    assert lot_device.created
    assert lot_device.author_id == g.user.id
    assert device.parents == {lot}


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_add_edge():
    child = Lot(name='child')
    parent = Lot(name='parent')
    db.session.add(child)
    db.session.add(parent)
    db.session.flush()
    # todo edges should automatically be created when the lot is created
    child.edges.add(Edge(path=Ltree(str(child.id).replace('-', '_'))))
    parent.edges.add(Edge(path=Ltree(str(parent.id).replace('-', '_'))))
    db.session.flush()

    parent.add_child(child)

    assert child in parent
    assert len(child.edges) == 1
    assert len(parent.edges) == 1

    parent.remove_child(child)
    assert child not in parent
    assert len(child.edges) == 1
    assert len(parent.edges) == 1

    grandparent = Lot(name='grandparent')
    db.session.add(grandparent)
    db.session.flush()
    grandparent.edges.add(Edge(path=Ltree(str(grandparent.id).replace('-', '_'))))
    db.session.flush()

    grandparent.add_child(parent)
    parent.add_child(child)

    assert parent in grandparent
    assert child in parent
    assert child in grandparent
