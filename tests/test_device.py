import datetime
from datetime import timedelta
from uuid import UUID

import pytest
from colour import Color
from ereuse_utils.naming import Naming
from ereuse_utils.test import ANY
from pytest import raises
from sqlalchemy.util import OrderedSet
from teal.db import ResourceNotFound

from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.device.exceptions import NeedsId
from ereuse_devicehub.resources.device.models import Component, ComputerMonitor, DataStorage, \
    Desktop, Device, GraphicCard, Laptop, Motherboard, NetworkAdapter
from ereuse_devicehub.resources.device.schemas import Device as DeviceS
from ereuse_devicehub.resources.device.search import DeviceSearch
from ereuse_devicehub.resources.device.sync import MismatchBetweenTags, MismatchBetweenTagsAndHid, \
    Sync
from ereuse_devicehub.resources.enums import ComputerChassis, DisplayTech
from ereuse_devicehub.resources.event import models as m
from ereuse_devicehub.resources.event.models import Remove, Test
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.resources.user import User
from tests import conftest
from tests.conftest import file


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_device_model():
    """
    Tests that the correctness of the device model and its relationships.
    """
    pc = Desktop(model='p1mo',
                 manufacturer='p1ma',
                 serial_number='p1s',
                 chassis=ComputerChassis.Tower)
    net = NetworkAdapter(model='c1mo', manufacturer='c1ma', serial_number='c1s')
    graphic = GraphicCard(model='c2mo', manufacturer='c2ma', memory=1500)
    pc.components.add(net)
    pc.components.add(graphic)
    db.session.add(pc)
    db.session.commit()
    pc = Desktop.query.one()
    assert pc.serial_number == 'p1s'
    assert pc.components == OrderedSet([net, graphic])
    network_adapter = NetworkAdapter.query.one()
    assert network_adapter.parent == pc

    # Removing a component from pc doesn't delete the component
    pc.components.remove(net)
    db.session.commit()
    pc = Device.query.first()  # this is the same as querying for Desktop directly
    assert pc.components == {graphic}
    network_adapter = NetworkAdapter.query.one()
    assert network_adapter not in pc.components
    assert network_adapter.parent is None

    # Deleting the pc deletes everything
    gcard = GraphicCard.query.one()
    db.session.delete(pc)
    db.session.flush()
    assert pc.id == 1
    assert Desktop.query.first() is None
    db.session.commit()
    assert Desktop.query.first() is None
    assert network_adapter.id == 2
    assert NetworkAdapter.query.first() is not None, 'We removed the network adaptor'
    assert gcard.id == 3, 'We should still hold a reference to a zombie graphic card'
    assert GraphicCard.query.first() is None, 'We should have deleted it –it was inside the pc'


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_device_schema():
    """Ensures the user does not upload non-writable or extra fields."""
    device_s = DeviceS()
    device_s.load({'serialNumber': 'foo1', 'model': 'foo', 'manufacturer': 'bar2'})
    device_s.dump(Device(id=1))


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_physical_properties():
    c = Motherboard(slots=2,
                    usb=3,
                    serial_number='sn',
                    model='ml',
                    manufacturer='mr',
                    width=2.0,
                    color=Color())
    pc = Desktop(chassis=ComputerChassis.Tower)
    pc.components.add(c)
    db.session.add(pc)
    db.session.commit()
    assert c.physical_properties == {
        'usb': 3,
        'serial_number': 'sn',
        'pcmcia': None,
        'model': 'ml',
        'slots': 2,
        'serial': None,
        'firewire': None,
        'manufacturer': 'mr',
        'weight': None,
        'height': None,
        'width': 2.0,
        'color': Color(),
        'depth': None
    }


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_component_similar_one():
    snapshot = conftest.file('pc-components.db')
    d = snapshot['device']
    snapshot['components'][0]['serial_number'] = snapshot['components'][1]['serial_number'] = None
    pc = Desktop(**d, components=OrderedSet(Component(**c) for c in snapshot['components']))
    component1, component2 = pc.components  # type: Component
    db.session.add(pc)
    db.session.flush()
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
    values = conftest.file('pc-components.db')
    pc = values['device']
    c1, c2 = (Component(**c) for c in values['components'])
    pc = Desktop(**pc, components=OrderedSet([c1, c2]))
    db.session.add(pc)
    c3 = Component(serial_number='nc1')
    pc2 = Desktop(serial_number='s2',
                  components=OrderedSet([c3]),
                  chassis=ComputerChassis.Microtower)
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
    assert events[0].components == OrderedSet([c3])


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_sync_run_components_empty():
    """
    Syncs a device that has an empty components list. The system should
    remove all the components from the device.
    """
    s = conftest.file('pc-components.db')
    pc = Desktop(**s['device'], components=OrderedSet(Component(**c) for c in s['components']))
    db.session.add(pc)
    db.session.commit()

    # Create a new transient non-db synced object
    pc = Desktop(**s['device'])
    db_pc, _ = Sync().run(pc, components=OrderedSet())
    assert not db_pc.components
    assert not pc.components


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_sync_run_components_none():
    """
    Syncs a device that has a None components. The system should
    keep all the components from the device.
    """
    s = conftest.file('pc-components.db')
    pc = Desktop(**s['device'], components=OrderedSet(Component(**c) for c in s['components']))
    db.session.add(pc)
    db.session.commit()

    # Create a new transient non-db synced object
    transient_pc = Desktop(**s['device'])
    db_pc, _ = Sync().run(transient_pc, components=None)
    assert db_pc.components
    assert db_pc.components == pc.components


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_sync_execute_register_desktop_new_Desktop_no_tag():
    """
    Syncs a new Desktop with HID and without a tag, creating it.
    :return:
    """
    # Case 1: device does not exist on DB
    pc = Desktop(**conftest.file('pc-components.db')['device'])
    db_pc = Sync().execute_register(pc)
    assert pc.physical_properties == db_pc.physical_properties


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_sync_execute_register_desktop_existing_no_tag():
    """
    Syncs an existing Desktop with HID and without a tag.
    """
    pc = Desktop(**conftest.file('pc-components.db')['device'])
    db.session.add(pc)
    db.session.commit()

    pc = Desktop(
        **conftest.file('pc-components.db')['device'])  # Create a new transient non-db object
    # 1: device exists on DB
    db_pc = Sync().execute_register(pc)
    assert pc.physical_properties == db_pc.physical_properties


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_sync_execute_register_desktop_no_hid_no_tag():
    """
    Syncs a Desktop without HID and no tag.

    This should fail as we don't have a way to identify it.
    """
    pc = Desktop(**conftest.file('pc-components.db')['device'])
    # 1: device has no HID
    pc.hid = pc.model = None
    with pytest.raises(NeedsId):
        Sync().execute_register(pc)


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_sync_execute_register_desktop_tag_not_linked():
    """
    Syncs a new Desktop with HID and a non-linked tag.

    It is OK if the tag was not linked, it will be linked in this process.
    """
    tag = Tag(id='foo')
    db.session.add(tag)
    db.session.commit()

    # Create a new transient non-db object
    pc = Desktop(**conftest.file('pc-components.db')['device'], tags=OrderedSet([Tag(id='foo')]))
    returned_pc = Sync().execute_register(pc)
    assert returned_pc == pc
    assert tag.device == pc, 'Tag has to be linked'
    assert Desktop.query.one() == pc, 'Desktop had to be set to db'


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_sync_execute_register_no_hid_tag_not_linked(tag_id: str):
    """
    Validates registering a Desktop without HID and a non-linked tag.

    In this case it is ok still, as the non-linked tag proves that
    the Desktop was not existing before (otherwise the tag would
    be linked), and thus it creates a new Desktop.
    """
    tag = Tag(id=tag_id)
    pc = Desktop(**conftest.file('pc-components.db')['device'], tags=OrderedSet([tag]))
    returned_pc = Sync().execute_register(pc)
    db.session.commit()
    assert returned_pc == pc
    db_tag = next(iter(returned_pc.tags))
    # they are not the same tags though
    # tag is a transient obj and db_tag the one from the db
    # they have the same pk though
    assert tag != db_tag, 'They are not the same tags though'
    assert db_tag.id == tag.id
    assert Desktop.query.one() == pc, 'Desktop had to be set to db'


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_sync_execute_register_tag_does_not_exist():
    """
    Ensures not being able to register if the tag does not exist,
    even if the device has HID or it existed before.

    Tags have to be created before trying to link them through a Snapshot.
    """
    pc = Desktop(**conftest.file('pc-components.db')['device'], tags=OrderedSet([Tag('foo')]))
    with raises(ResourceNotFound):
        Sync().execute_register(pc)


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_sync_execute_register_tag_linked_same_device():
    """
    If the tag is linked to the device, regardless if it has HID,
    the system should match the device through the tag.
    (If it has HID it validates both HID and tag point at the same
    device, this his checked in ).
    """
    orig_pc = Desktop(**conftest.file('pc-components.db')['device'])
    db.session.add(Tag(id='foo', device=orig_pc))
    db.session.commit()

    pc = Desktop(
        **conftest.file('pc-components.db')['device'])  # Create a new transient non-db object
    pc.tags.add(Tag(id='foo'))
    db_pc = Sync().execute_register(pc)
    assert db_pc.id == orig_pc.id
    assert len(db_pc.tags) == 1
    assert next(iter(db_pc.tags)).id == 'foo'


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_sync_execute_register_tag_linked_other_device_mismatch_between_tags():
    """
    Checks that sync raises an error if finds that at least two passed-in
    tags are not linked to the same device.
    """
    pc1 = Desktop(**conftest.file('pc-components.db')['device'])
    db.session.add(Tag(id='foo-1', device=pc1))
    pc2 = Desktop(**conftest.file('pc-components.db')['device'])
    pc2.serial_number = 'pc2-serial'
    pc2.hid = Naming.hid(pc2.manufacturer, pc2.serial_number, pc2.model)
    db.session.add(Tag(id='foo-2', device=pc2))
    db.session.commit()

    pc1 = Desktop(
        **conftest.file('pc-components.db')['device'])  # Create a new transient non-db object
    pc1.tags.add(Tag(id='foo-1'))
    pc1.tags.add(Tag(id='foo-2'))
    with raises(MismatchBetweenTags):
        Sync().execute_register(pc1)


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_sync_execute_register_mismatch_between_tags_and_hid():
    """
    Checks that sync raises an error if it finds that the HID does
    not point at the same device as the tag does.

    In this case we set HID -> pc1 but tag -> pc2
    """
    pc1 = Desktop(**conftest.file('pc-components.db')['device'])
    db.session.add(Tag(id='foo-1', device=pc1))
    pc2 = Desktop(**conftest.file('pc-components.db')['device'])
    pc2.serial_number = 'pc2-serial'
    pc2.hid = Naming.hid(pc2.manufacturer, pc2.serial_number, pc2.model)
    db.session.add(Tag(id='foo-2', device=pc2))
    db.session.commit()

    pc1 = Desktop(
        **conftest.file('pc-components.db')['device'])  # Create a new transient non-db object
    pc1.tags.add(Tag(id='foo-2'))
    with raises(MismatchBetweenTagsAndHid):
        Sync().execute_register(pc1)


def test_get_device(app: Devicehub, user: UserClient):
    """Checks GETting a Desktop with its components."""
    with app.app_context():
        pc = Desktop(model='p1mo',
                     manufacturer='p1ma',
                     serial_number='p1s',
                     chassis=ComputerChassis.Tower)
        pc.components = OrderedSet([
            NetworkAdapter(model='c1mo', manufacturer='c1ma', serial_number='c1s'),
            GraphicCard(model='c2mo', manufacturer='c2ma', memory=1500)
        ])
        db.session.add(pc)
        db.session.add(Test(device=pc,
                            elapsed=timedelta(seconds=4),
                            error=False,
                            agent=Person(name='Timmy'),
                            author=User(email='bar@bar.com')))
        db.session.commit()
    pc, _ = user.get(res=Device, item=1)
    assert len(pc['events']) == 1
    assert pc['events'][0]['type'] == 'Test'
    assert pc['events'][0]['device'] == 1
    assert pc['events'][0]['elapsed'] == 4
    assert not pc['events'][0]['error']
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
        pc = Desktop(model='p1mo',
                     manufacturer='p1ma',
                     serial_number='p1s',
                     chassis=ComputerChassis.Tower)
        pc.components = OrderedSet([
            NetworkAdapter(model='c1mo', manufacturer='c1ma', serial_number='c1s'),
            GraphicCard(model='c2mo', manufacturer='c2ma', memory=1500)
        ])
        pc1 = Desktop(model='p2mo',
                      manufacturer='p2ma',
                      serial_number='p2s',
                      chassis=ComputerChassis.Tower)
        pc2 = Laptop(model='p3mo',
                     manufacturer='p3ma',
                     serial_number='p3s',
                     chassis=ComputerChassis.Netbook)
        db.session.add_all((pc, pc1, pc2))
        db.session.commit()
    devices, _ = user.get(res=Device)
    assert tuple(d['id'] for d in devices['items']) == (1, 2, 3, 4, 5)
    assert tuple(d['type'] for d in devices['items']) == (
        'Desktop', 'Desktop', 'Laptop', 'NetworkAdapter', 'GraphicCard'
    )


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_computer_monitor():
    m = ComputerMonitor(technology=DisplayTech.LCD,
                        manufacturer='foo',
                        model='bar',
                        serial_number='foo-bar',
                        resolution_width=1920,
                        resolution_height=1080,
                        size=14.5)
    db.session.add(m)
    db.session.commit()


@pytest.mark.xfail(reason='Make test')
def test_mobile_meid():
    pass


@pytest.mark.xfail(reason='Make test')
def test_mobile_imei():
    pass


@pytest.mark.xfail(reason='Make test')
def test_computer_with_display():
    pass


def test_device_search_all_devices_token_if_empty(app: Devicehub, user: UserClient):
    """Ensures DeviceSearch can regenerate itself when the table is empty."""
    user.post(file('basic.snapshot'), res=m.Snapshot)
    with app.app_context():
        app.db.session.execute('TRUNCATE TABLE {}'.format(DeviceSearch.__table__.name))
        app.db.session.commit()
    i, _ = user.get(res=Device, query=[('search', 'Desktop')])
    assert not len(i['items'])
    with app.app_context():
        DeviceSearch.set_all_devices_tokens_if_empty(app.db.session)
    i, _ = user.get(res=Device, query=[('search', 'Desktop')])
    assert not len(i['items'])


def test_manufacturer(user: UserClient):
    m, r = user.get(res='Manufacturer', query=[('name', 'asus')])
    assert m == {'items': [{'name': 'Asus', 'url': 'https://en.wikipedia.org/wiki/Asus'}]}
    assert r.cache_control.public
    assert r.expires > datetime.datetime.now()


@pytest.mark.xfail(reason='Develop functionality')
def test_manufacturer_enforced():
    """Ensures that non-computer devices can submit only
     manufacturers from the Manufacturer table."""


def test_device_properties_format(app: Devicehub, user: UserClient):
    user.post(file('asus-eee-1000h.snapshot.11'), res=m.Snapshot)
    with app.app_context():
        pc = Laptop.query.one()  # type: Laptop
        assert format(pc) == 'Laptop 1: model 1000h, S/N 94oaaq021116'
        assert format(pc, 't') == 'netbook 1000h'
        assert format(pc, 's') == '(asustek computer inc.) S/N 94oaaq021116'
        assert pc.ram_size == 1024
        assert pc.data_storage_size == 152627
        assert pc.graphic_card_model == 'mobile 945gse express integrated graphics controller'
        assert pc.processor_model == 'intel atom cpu n270 @ 1.60ghz'
        net = next(c for c in pc.components if isinstance(c, NetworkAdapter))
        assert format(net) == 'NetworkAdapter 2: model ar8121/ar8113/ar8114 ' \
                              'gigabit or fast ethernet, S/N 00:24:8c:7f:cf:2d'
        assert format(net, 't') == 'NetworkAdapter ar8121/ar8113/ar8114 gigabit or fast ethernet'
        assert format(net, 's') == '(qualcomm atheros) S/N 00:24:8c:7f:cf:2d – 100 Mbps'
        hdd = next(c for c in pc.components if isinstance(c, DataStorage))
        assert format(hdd) == 'HardDrive 7: model st9160310as, S/N 5sv4tqa6'
        assert format(hdd, 't') == 'HardDrive st9160310as'
        assert format(hdd, 's') == '(seagate) S/N 5sv4tqa6 – 152 GB'


def test_device_public(user: UserClient, client: Client):
    s, _ = user.post(file('asus-eee-1000h.snapshot.11'), res=m.Snapshot)
    html, _ = client.get(res=Device, item=s['device']['id'], accept=ANY)
    assert 'intel atom cpu n270 @ 1.60ghz' in html
    assert 'S/N 00:24:8c:7f:cf:2d – 100 Mbps' in html


@pytest.mark.xfail(reason='Functionality not yet developed.')
def test_device_search_multiple_tags(user: UserClient):
    """Ensures that users can search multiple tags at once
    and get their multiple devices."""
    pass
