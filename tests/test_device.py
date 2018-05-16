from datetime import timedelta
from uuid import UUID

import pytest

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.exceptions import NeedsId
from ereuse_devicehub.resources.device.models import Component, Computer, Desktop, Device, \
    GraphicCard, Laptop, Microtower, Motherboard, NetworkAdapter
from ereuse_devicehub.resources.device.schemas import Device as DeviceS
from ereuse_devicehub.resources.device.sync import Sync
from ereuse_devicehub.resources.event.models import Remove, Test
from ereuse_devicehub.resources.user import User
from teal.db import ResourceNotFound
from tests.conftest import file


@pytest.mark.usefixtures('app_context')
def test_device_model():
    """
    Tests that the correctness of the device model and its relationships.
    """
    pc = Desktop(model='p1mo', manufacturer='p1ma', serial_number='p1s')
    pc.components = components = [
        NetworkAdapter(model='c1mo', manufacturer='c1ma', serial_number='c1s'),
        GraphicCard(model='c2mo', manufacturer='c2ma', memory=1500)
    ]
    db.session.add(pc)
    db.session.commit()
    pc = Desktop.query.one()
    assert pc.serial_number == 'p1s'
    assert pc.components == components
    network_adapter = NetworkAdapter.query.one()
    assert network_adapter.parent == pc

    # Removing a component from pc doesn't delete the component
    del pc.components[0]
    db.session.commit()
    pc = Device.query.first()  # this is the same as querying for Desktop directly
    assert pc.components[0].type == GraphicCard.__name__
    network_adapter = NetworkAdapter.query.one()
    assert network_adapter not in pc.components
    assert network_adapter.parent is None

    # Deleting the pc deletes everything
    gcard = GraphicCard.query.one()
    db.session.delete(pc)
    assert pc.id == 1
    assert Desktop.query.first() is None
    db.session.commit()
    assert Desktop.query.first() is None
    assert network_adapter.id == 2
    assert NetworkAdapter.query.first() is not None, 'We removed the network adaptor'
    assert gcard.id == 3, 'We should still hold a reference to a zombie graphic card'
    assert GraphicCard.query.first() is None, 'We should have deleted it –it was inside the pc'


@pytest.mark.usefixtures('app_context')
def test_device_schema():
    """Ensures the user does not upload non-writable or extra fields."""
    device_s = DeviceS()
    device_s.load({'serialNumber': 'foo1', 'model': 'foo', 'manufacturer': 'bar2'})
    device_s.dump(Device(id=1))


@pytest.mark.usefixtures('app_context')
def test_physical_properties():
    c = Motherboard(slots=2,
                    usb=3,
                    serial_number='sn',
                    model='ml',
                    manufacturer='mr',
                    width=2.0,
                    pid='abc')
    pc = Computer(components=[c])
    db.session.add(pc)
    db.session.commit()
    assert c.physical_properties == {
        'gid': None,
        'usb': 3,
        'pid': 'abc',
        'serial_number': 'sn',
        'pcmcia': None,
        'model': 'ml',
        'slots': 2,
        'serial': None,
        'firewire': None,
        'manufacturer': 'mr',
        'weight': None,
        'height': None,
        'width': 2.0
    }


@pytest.mark.usefixtures('app_context')
def test_component_similar_one():
    snapshot = file('pc-components.db')
    d = snapshot['device']
    snapshot['components'][0]['serial_number'] = snapshot['components'][1]['serial_number'] = None
    pc = Computer(**d, components=[Component(**c) for c in snapshot['components']])
    component1, component2 = pc.components  # type: Component
    db.session.add(pc)
    # Let's create a new component named 'A' similar to 1
    componentA = Component(model=component1.model, manufacturer=component1.manufacturer)
    similar_to_a = componentA.similar_one(pc, set())
    assert similar_to_a == component1
    # Component B does not have the same model
    componentB = Component(model='nope', manufacturer=component1.manufacturer)
    with pytest.raises(ResourceNotFound):
        assert componentB.similar_one(pc, set())
    # If we blacklist component A we won't get anything
    with pytest.raises(ResourceNotFound):
        assert componentA.similar_one(pc, blacklist={componentA.id})


@pytest.mark.usefixtures('auth_app_context')
def test_add_remove():
    # Original state:
    # pc has c1 and c2
    # pc2 has c3
    # c4 is not with any pc
    values = file('pc-components.db')
    pc = values['device']
    c1, c2 = [Component(**c) for c in values['components']]
    pc = Computer(**pc, components=[c1, c2])
    db.session.add(pc)
    c3 = Component(serial_number='nc1')
    pc2 = Computer(serial_number='s2', components=[c3])
    c4 = Component(serial_number='c4s')
    db.session.add(pc2)
    db.session.add(c4)
    db.session.commit()

    # Test:
    # pc has only c3
    events = Sync.add_remove(device=pc, components={c3, c4})
    db.session.add_all(events)
    db.session.commit()  # We enforce the appliance of order_by
    assert len(events) == 1
    assert isinstance(events[0], Remove)
    assert events[0].device == pc2
    assert events[0].components == [c3]


@pytest.mark.usefixtures('app_context')
def test_execute_register_computer():
    # Case 1: device does not exist on DB
    pc = Computer(**file('pc-components.db')['device'])
    db_pc, _ = Sync.execute_register(pc, set())
    assert pc.physical_properties == db_pc.physical_properties


@pytest.mark.usefixtures('app_context')
def test_execute_register_computer_existing():
    pc = Computer(**file('pc-components.db')['device'])
    db.session.add(pc)
    db.session.commit()  # We need two separate sessions
    pc = Computer(**file('pc-components.db')['device'])
    # 1: device exists on DB
    db_pc, _ = Sync.execute_register(pc, set())
    assert pc.physical_properties == db_pc.physical_properties


@pytest.mark.usefixtures('app_context')
def test_execute_register_computer_no_hid():
    pc = Computer(**file('pc-components.db')['device'])
    # 1: device has no HID
    pc.hid = pc.model = None
    with pytest.raises(NeedsId):
        Sync.execute_register(pc, set())


def test_get_device(app: Devicehub, user: UserClient):
    """Checks GETting a Desktop with its components."""
    with app.app_context():
        pc = Desktop(model='p1mo', manufacturer='p1ma', serial_number='p1s')
        pc.components = [
            NetworkAdapter(model='c1mo', manufacturer='c1ma', serial_number='c1s'),
            GraphicCard(model='c2mo', manufacturer='c2ma', memory=1500)
        ]
        db.session.add(pc)
        db.session.add(Test(device=pc,
                            elapsed=timedelta(seconds=4),
                            success=True,
                            author=User(email='bar@bar.com')))
        db.session.commit()
    pc, _ = user.get(res=Device, item=1)
    assert len(pc['events']) == 1
    assert pc['events'][0]['type'] == 'Test'
    assert pc['events'][0]['id'] == 1
    assert pc['events'][0]['device'] == 1
    assert pc['events'][0]['elapsed'] == 4
    assert pc['events'][0]['success'] == True
    assert UUID(pc['events'][0]['author'])
    assert 'events_components' not in pc, 'events_components are internal use only'
    assert 'events_one' not in pc, 'they are internal use only'
    assert 'author' not in pc
    assert tuple(c['id'] for c in pc['components']) == (2, 3)
    assert pc['hid'] == 'p1ma-p1s-p1mo'
    assert pc['model'] == 'p1mo'
    assert pc['manufacturer'] == 'p1ma'
    assert pc['serialNumber'] == 'p1s'
    assert pc['type'] == 'Desktop'


def test_get_devices(app: Devicehub, user: UserClient):
    """Checks GETting multiple devices."""
    with app.app_context():
        pc = Desktop(model='p1mo', manufacturer='p1ma', serial_number='p1s')
        pc.components = [
            NetworkAdapter(model='c1mo', manufacturer='c1ma', serial_number='c1s'),
            GraphicCard(model='c2mo', manufacturer='c2ma', memory=1500)
        ]
        pc1 = Microtower(model='p2mo', manufacturer='p2ma', serial_number='p2s')
        pc2 = Laptop(model='p3mo', manufacturer='p3ma', serial_number='p3s')
        db.session.add_all((pc, pc1, pc2))
        db.session.commit()
    devices, _ = user.get(res=Device)
    assert tuple(d['id'] for d in devices) == (1, 2, 3, 4, 5)
    assert tuple(d['type'] for d in devices) == ('Desktop', 'Microtower',
                                                 'Laptop', 'NetworkAdapter', 'GraphicCard')
