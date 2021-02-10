import copy
import datetime
import pytest

from uuid import UUID
from flask import g

from colour import Color
from ereuse_utils.naming import Naming
from ereuse_utils.test import ANY
from pytest import raises
from sqlalchemy.util import OrderedSet
from teal.db import ResourceNotFound
from teal.enums import Layouts

from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.action import models as m
from ereuse_devicehub.resources.action.models import Remove, TestConnectivity
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.device import models as d
from ereuse_devicehub.resources.device.exceptions import NeedsId
from ereuse_devicehub.resources.device.schemas import Device as DeviceS
from ereuse_devicehub.resources.device.sync import MismatchBetweenTags, MismatchBetweenTagsAndHid, \
    Sync
from ereuse_devicehub.resources.enums import ComputerChassis, DisplayTech, Severity, \
    SnapshotSoftware, TransferState
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.resources.user import User
from tests import conftest
from tests.conftest import file


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_device_model():
    """Tests that the correctness of the device model and its relationships."""
    pc = d.Desktop(model='p1mo',
                   manufacturer='p1ma',
                   serial_number='p1s',
                   chassis=ComputerChassis.Tower)
    net = d.NetworkAdapter(model='c1mo', manufacturer='c1ma', serial_number='c1s')
    graphic = d.GraphicCard(model='c2mo', manufacturer='c2ma', memory=1500)
    pc.components.add(net)
    pc.components.add(graphic)
    db.session.add(pc)
    db.session.commit()
    pc = d.Desktop.query.one()
    assert pc.serial_number == 'p1s'
    assert pc.components == OrderedSet([net, graphic])
    network_adapter = d.NetworkAdapter.query.one()
    assert network_adapter.parent == pc

    # Removing a component from pc doesn't delete the component
    pc.components.remove(net)
    db.session.commit()
    pc = d.Device.query.filter_by(id=pc.id).first()  # this is the same as querying for d.Desktop directly
    assert pc.components == {graphic}
    network_adapter = d.NetworkAdapter.query.one()
    assert network_adapter not in pc.components
    assert network_adapter.parent is None

    # Deleting the pc deletes everything
    gcard = d.GraphicCard.query.one()
    db.session.delete(pc)
    db.session.flush()
    assert pc.id == 1
    assert d.Desktop.query.first() is None
    db.session.commit()
    assert d.Desktop.query.first() is None
    assert network_adapter.id == 2
    assert d.NetworkAdapter.query.first() is not None, 'We removed the network adaptor'
    assert gcard.id == 3, 'We should still hold a reference to a zombie graphic card'
    assert d.GraphicCard.query.first() is None, 'We should have deleted it –it was inside the pc'


@pytest.mark.xfail(reason='Test not developed')
def test_device_problems():
    pass


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_device_schema():
    """Ensures the user does not upload non-writable or extra fields."""
    device_s = DeviceS()
    device_s.load({'serialNumber': 'foo1', 'model': 'foo', 'manufacturer': 'bar2'})
    device_s.dump(d.Device(id=1))


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_physical_properties():
    c = d.Motherboard(slots=2,
                      usb=3,
                      serial_number='sn',
                      model='ml',
                      manufacturer='mr',
                      width=2.0,
                      color=Color())
    pc = d.Desktop(chassis=ComputerChassis.Tower,
                   model='foo',
                   manufacturer='bar',
                   serial_number='foo-bar',
                   weight=2.8,
                   width=1.4,
                   height=2.1,
                   color=Color('LightSeaGreen'))
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
        'bios_date': None,
        'ram_max_size': None,
        'ram_slots': None
    }
    assert pc.physical_properties == {
        'chassis': ComputerChassis.Tower,
        'amount': 0,
        'manufacturer': 'bar',
        'model': 'foo',
        'receiver_id': None,
        'serial_number': 'foo-bar',
        'transfer_state': TransferState.Initial
    }


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_component_similar_one():
    user = User.query.filter().first()
    snapshot = conftest.file('pc-components.db')
    pc = snapshot['device']
    snapshot['components'][0]['serial_number'] = snapshot['components'][1]['serial_number'] = None
    pc = d.Desktop(**pc, components=OrderedSet(d.Component(**c) for c in snapshot['components']))
    component1, component2 = pc.components  # type: d.Component
    db.session.add(pc)
    db.session.flush()
    # Let's create a new component named 'A' similar to 1
    componentA = d.Component(model=component1.model, manufacturer=component1.manufacturer,
                             owner_id=user.id)
    similar_to_a = componentA.similar_one(pc, set())
    assert similar_to_a == component1
    # d.Component B does not have the same model
    componentB = d.Component(model='nope', manufacturer=component1.manufacturer)
    with pytest.raises(ResourceNotFound):
        assert componentB.similar_one(pc, set())
    # If we blacklist component A we won't get anything
    with pytest.raises(ResourceNotFound):
        assert componentA.similar_one(pc, blacklist={componentA.id})


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_add_remove():
    # Original state:
    # pc has c1 and c2
    # pc2 has c3
    # c4 is not with any pc
    user = User.query.filter().first()
    values = conftest.file('pc-components.db')
    pc = values['device']
    c1, c2 = (d.Component(**c) for c in values['components'])
    pc = d.Desktop(**pc, components=OrderedSet([c1, c2]))
    db.session.add(pc)
    c3 = d.Component(serial_number='nc1', owner_id=user.id)
    pc2 = d.Desktop(serial_number='s2',
                    components=OrderedSet([c3]),
                    chassis=ComputerChassis.Microtower)
    c4 = d.Component(serial_number='c4s', owner_id=user.id)
    db.session.add(pc2)
    db.session.add(c4)
    db.session.commit()

    # Test:
    # pc has only c3
    actions = Sync.add_remove(device=pc, components={c3, c4})
    db.session.add_all(actions)
    db.session.commit()  # We enforce the appliance of order_by
    assert len(actions) == 1
    assert isinstance(actions[0], Remove)
    assert actions[0].device == pc2
    assert actions[0].components == OrderedSet([c3])


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_sync_run_components_empty():
    """Syncs a device that has an empty components list. The system should
    remove all the components from the device.
    """
    s = conftest.file('pc-components.db')
    pc = d.Desktop(**s['device'], components=OrderedSet(d.Component(**c) for c in s['components']))
    db.session.add(pc)
    db.session.commit()

    # Create a new transient non-db synced object
    pc = d.Desktop(**s['device'])
    db_pc, _ = Sync().run(pc, components=OrderedSet())
    assert not db_pc.components
    assert not pc.components


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_sync_run_components_none():
    """Syncs a device that has a None components. The system should
    keep all the components from the device.
    """
    s = conftest.file('pc-components.db')
    pc = d.Desktop(**s['device'], components=OrderedSet(d.Component(**c) for c in s['components']))
    db.session.add(pc)
    db.session.commit()

    # Create a new transient non-db synced object
    transient_pc = d.Desktop(**s['device'])
    db_pc, _ = Sync().run(transient_pc, components=None)
    assert db_pc.components
    assert db_pc.components == pc.components


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_sync_execute_register_desktop_new_desktop_no_tag():
    """Syncs a new d.Desktop with HID and without a tag, creating it."""
    # Case 1: device does not exist on DB
    pc = d.Desktop(**conftest.file('pc-components.db')['device'])
    db_pc = Sync().execute_register(pc)
    assert pc.physical_properties == db_pc.physical_properties


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_sync_execute_register_desktop_existing_no_tag():
    """Syncs an existing d.Desktop with HID and without a tag."""
    pc = d.Desktop(**conftest.file('pc-components.db')['device'])
    db.session.add(pc)
    db.session.commit()

    pc = d.Desktop(
        **conftest.file('pc-components.db')['device'])  # Create a new transient non-db object
    # 1: device exists on DB
    db_pc = Sync().execute_register(pc)
    pc.amount = 0
    pc.owner_id = db_pc.owner_id
    pc.transfer_state = TransferState.Initial
    assert pc.physical_properties == db_pc.physical_properties


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_sync_execute_register_desktop_no_hid_no_tag(user: UserClient):
    """Syncs a d.Desktop without HID and no tag.
    This should not fail as we don't have a way to identify it.
    """
    device = conftest.file('pc-components.db')['device']
    device['owner_id'] = user.user['id']
    pc = d.Desktop(**device)
    # 1: device has no HID
    pc.hid = pc.model = None
    returned_pc = Sync().execute_register(pc)
    assert returned_pc == pc


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_sync_execute_register_desktop_tag_not_linked():
    """Syncs a new d.Desktop with HID and a non-linked tag.

    It is OK if the tag was not linked, it will be linked in this process.
    """
    tag = Tag(id='foo')
    db.session.add(tag)
    db.session.commit()

    # Create a new transient non-db object
    pc = d.Desktop(**conftest.file('pc-components.db')['device'], tags=OrderedSet([Tag(id='foo')]))
    returned_pc = Sync().execute_register(pc)
    assert returned_pc == pc
    assert tag.device == pc, 'Tag has to be linked'
    assert d.Desktop.query.one() == pc, 'd.Desktop had to be set to db'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_sync_execute_register_no_hid_tag_not_linked(tag_id: str):
    """Validates registering a d.Desktop without HID and a non-linked tag.

    In this case it is ok still, as the non-linked tag proves that
    the d.Desktop was not existing before (otherwise the tag would
    be linked), and thus it creates a new d.Desktop.
    """
    tag = Tag(id=tag_id)
    pc = d.Desktop(**conftest.file('pc-components.db')['device'], tags=OrderedSet([tag]))
    db.session.add(g.user)
    returned_pc = Sync().execute_register(pc)
    db.session.commit()
    assert returned_pc == pc
    db_tag = next(iter(returned_pc.tags))
    # they are not the same tags though
    # tag is a transient obj and db_tag the one from the db
    # they have the same pk though
    assert tag != db_tag, 'They are not the same tags though'
    assert db_tag.id == tag.id
    assert d.Desktop.query.one() == pc, 'd.Desktop had to be set to db'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_sync_execute_register_tag_does_not_exist():
    """Ensures not being able to register if the tag does not exist,
    even if the device has HID or it existed before.

    Tags have to be created before trying to link them through a Snapshot.
    """
    user = User.query.filter().first()
    pc = d.Desktop(**conftest.file('pc-components.db')['device'], tags=OrderedSet([Tag('foo')]))
    pc.owner_id = user.id
    with raises(ResourceNotFound):
        Sync().execute_register(pc)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_sync_execute_register_tag_linked_same_device():
    """If the tag is linked to the device, regardless if it has HID,
    the system should match the device through the tag.
    (If it has HID it validates both HID and tag point at the same
    device, this his checked in ).
    """
    orig_pc = d.Desktop(**conftest.file('pc-components.db')['device'])
    db.session.add(Tag(id='foo', device=orig_pc))
    db.session.commit()

    pc = d.Desktop(
        **conftest.file('pc-components.db')['device'])  # Create a new transient non-db object
    pc.tags.add(Tag(id='foo'))
    db_pc = Sync().execute_register(pc)
    assert db_pc.id == orig_pc.id
    assert len(db_pc.tags) == 1
    assert next(iter(db_pc.tags)).id == 'foo'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_sync_execute_register_tag_linked_other_device_mismatch_between_tags():
    """Checks that sync raises an error if finds that at least two passed-in
    tags are not linked to the same device.
    """
    pc1 = d.Desktop(**conftest.file('pc-components.db')['device'])
    db.session.add(Tag(id='foo-1', device=pc1))
    pc2 = d.Desktop(**conftest.file('pc-components.db')['device'])
    pc2.serial_number = 'pc2-serial'
    pc2.hid = Naming.hid(pc2.type, pc2.manufacturer, pc2.model, pc2.serial_number)
    db.session.add(Tag(id='foo-2', device=pc2))
    db.session.commit()

    pc1 = d.Desktop(
        **conftest.file('pc-components.db')['device'])  # Create a new transient non-db object
    pc1.tags.add(Tag(id='foo-1'))
    pc1.tags.add(Tag(id='foo-2'))
    with raises(MismatchBetweenTags):
        Sync().execute_register(pc1)


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_sync_execute_register_mismatch_between_tags_and_hid():
    """Checks that sync raises an error if it finds that the HID does
    not point at the same device as the tag does.

    In this case we set HID -> pc1 but tag -> pc2
    """
    pc1 = d.Desktop(**conftest.file('pc-components.db')['device'])
    db.session.add(Tag(id='foo-1', device=pc1))
    pc2 = d.Desktop(**conftest.file('pc-components.db')['device'])
    pc2.serial_number = 'pc2-serial'
    pc2.hid = Naming.hid(pc2.type, pc2.manufacturer, pc2.model, pc2.serial_number)
    db.session.add(Tag(id='foo-2', device=pc2))
    db.session.commit()

    pc1 = d.Desktop(
        **conftest.file('pc-components.db')['device'])  # Create a new transient non-db object
    pc1.tags.add(Tag(id='foo-2'))
    with raises(MismatchBetweenTagsAndHid):
        Sync().execute_register(pc1)


@pytest.mark.mvp
def test_get_device(app: Devicehub, user: UserClient):
    """Checks GETting a d.Desktop with its components."""
    with app.app_context():
        pc = d.Desktop(model='p1mo',
                       manufacturer='p1ma',
                       serial_number='p1s',
                       chassis=ComputerChassis.Tower,
                       owner_id=user.user['id'])
        pc.components = OrderedSet([
            d.NetworkAdapter(model='c1mo', manufacturer='c1ma', serial_number='c1s', 
                owner_id=user.user['id']),
            d.GraphicCard(model='c2mo', manufacturer='c2ma', memory=1500, owner_id=user.user['id'])
        ])
        db.session.add(pc)
        # todo test is an abstract class. replace with another one
        db.session.add(TestConnectivity(device=pc,
                                        severity=Severity.Info,
                                        agent=Person(name='Timmy'),
                                        author=User(email='bar@bar.com')))
        db.session.commit()
    pc, _ = user.get(res=d.Device, item=1)
    assert len(pc['actions']) == 1
    assert pc['actions'][0]['type'] == 'TestConnectivity'
    assert pc['actions'][0]['device'] == 1
    assert pc['actions'][0]['severity'] == 'Info'
    assert UUID(pc['actions'][0]['author'])
    assert 'actions_components' not in pc, 'actions_components are internal use only'
    assert 'actions_one' not in pc, 'they are internal use only'
    assert 'author' not in pc
    assert tuple(c['id'] for c in pc['components']) == (2, 3)
    assert pc['hid'] == 'desktop-p1ma-p1mo-p1s'
    assert pc['model'] == 'p1mo'
    assert pc['manufacturer'] == 'p1ma'
    assert pc['serialNumber'] == 'p1s'
    assert pc['type'] == d.Desktop.t


@pytest.mark.mvp
def test_get_devices(app: Devicehub, user: UserClient):
    """Checks GETting multiple devices."""
    with app.app_context():
        pc = d.Desktop(model='p1mo',
                       manufacturer='p1ma',
                       serial_number='p1s',
                       chassis=ComputerChassis.Tower,
                       owner_id=user.user['id'])
        pc.components = OrderedSet([
            d.NetworkAdapter(model='c1mo', manufacturer='c1ma', serial_number='c1s',
                owner_id=user.user['id']),
            d.GraphicCard(model='c2mo', manufacturer='c2ma', memory=1500,
                owner_id=user.user['id'])
        ])
        pc1 = d.Desktop(model='p2mo',
                        manufacturer='p2ma',
                        serial_number='p2s',
                        chassis=ComputerChassis.Tower,
                        owner_id=user.user['id'])
        pc2 = d.Laptop(model='p3mo',
                       manufacturer='p3ma',
                       serial_number='p3s',
                       chassis=ComputerChassis.Netbook,
                       owner_id=user.user['id'])
        db.session.add_all((pc, pc1, pc2))
        db.session.commit()
    devices, _ = user.get(res=d.Device)
    assert tuple(dev['id'] for dev in devices['items']) == (1, 2, 3, 4, 5)
    assert tuple(dev['type'] for dev in devices['items']) == (
        d.Desktop.t, d.Desktop.t, d.Laptop.t, d.NetworkAdapter.t, d.GraphicCard.t
    )


@pytest.mark.mvp
def test_get_device_permissions(app: Devicehub, user: UserClient, user2: UserClient, 
        client: Client):
    """Checks GETting a d.Desktop with its components."""

    s, _ = user.post(file('asus-eee-1000h.snapshot.11'), res=m.Snapshot)
    pc, res = user.get(res=d.Device, item=s['device']['id'])
    assert res.status_code == 200
    assert len(pc['actions']) == 9

    html, _ = client.get(res=d.Device, item=s['device']['id'], accept=ANY)
    assert 'intel atom cpu n270 @ 1.60ghz' in html
    assert '00:24:8C:7F:CF:2D – 100 Mbps' in html
    pc2, res2 = user2.get(res=d.Device, item=s['device']['id'], accept=ANY)
    assert res2.status_code == 200
    assert pc2 == html


@pytest.mark.mvp
def test_get_devices_permissions(app: Devicehub, user: UserClient, user2: UserClient):
    """Checks GETting multiple devices."""

    user.post(file('asus-eee-1000h.snapshot.11'), res=m.Snapshot)
    url = '/devices/?filter={"type":["Computer"]}'

    devices, res = user.get(url, None)
    devices2, res2 = user2.get(url, None)
    assert res.status_code == 200
    assert res2.status_code == 200
    assert len(devices['items']) == 1
    assert len(devices2['items']) == 0

@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_computer_monitor():
    m = d.ComputerMonitor(technology=DisplayTech.LCD,
                          manufacturer='foo',
                          model='bar',
                          serial_number='foo-bar',
                          resolution_width=1920,
                          resolution_height=1080,
                          size=14.5)
    db.session.add(m)
    db.session.commit()


@pytest.mark.mvp
def test_manufacturer(user: UserClient):
    m, r = user.get(res='Manufacturer', query=[('search', 'asus')])
    assert m == {'items': [{'name': 'Asus', 'url': 'https://en.wikipedia.org/wiki/Asus'}]}
    assert r.cache_control.public
    assert r.expires > datetime.datetime.now()


@pytest.mark.mvp
@pytest.mark.xfail(reason='Develop functionality')
def test_manufacturer_enforced():
    """Ensures that non-computer devices can submit only
    manufacturers from the Manufacturer table.
    """


@pytest.mark.mvp
def test_device_properties_format(app: Devicehub, user: UserClient):
    user.post(file('asus-eee-1000h.snapshot.11'), res=m.Snapshot)
    with app.app_context():
        pc = d.Laptop.query.one()  # type: d.Laptop
        assert format(pc) == 'Laptop 1: model 1000h, S/N 94oaaq021116'
        assert format(pc, 't') == 'Netbook 1000h'
        assert format(pc, 's') == '(asustek computer inc.) S/N 94OAAQ021116'
        assert pc.ram_size == 1024
        assert pc.data_storage_size == 152627
        assert pc.graphic_card_model == 'mobile 945gse express integrated graphics controller'
        assert pc.processor_model == 'intel atom cpu n270 @ 1.60ghz'
        net = next(c for c in pc.components if isinstance(c, d.NetworkAdapter))
        assert format(net) == 'NetworkAdapter 2: model ar8121/ar8113/ar8114 ' \
                              'gigabit or fast ethernet, S/N 00:24:8c:7f:cf:2d'
        assert format(net, 't') == 'NetworkAdapter ar8121/ar8113/ar8114 gigabit or fast ethernet'
        assert format(net, 's') == 'qualcomm atheros 00:24:8C:7F:CF:2D – 100 Mbps'
        hdd = next(c for c in pc.components if isinstance(c, d.DataStorage))
        assert format(hdd) == 'HardDrive 7: model st9160310as, S/N 5sv4tqa6'
        assert format(hdd, 't') == 'HardDrive st9160310as'
        assert format(hdd, 's') == 'seagate 5SV4TQA6 – 152 GB'


@pytest.mark.mvp
def test_device_public(user: UserClient, client: Client):
    s, _ = user.post(file('asus-eee-1000h.snapshot.11'), res=m.Snapshot)
    html, _ = client.get(res=d.Device, item=s['device']['id'], accept=ANY)
    assert 'intel atom cpu n270 @ 1.60ghz' in html
    assert '00:24:8C:7F:CF:2D – 100 Mbps' in html


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_computer_accessory_model(user: UserClient):
    sai = d.SAI(owner_id=user.user['id'])
    db.session.add(sai)
    keyboard = d.Keyboard(layout=Layouts.ES, owner_id=user.user['id'])
    db.session.add(keyboard)
    mouse = d.Mouse(owner_id=user.user['id'])
    db.session.add(mouse)
    db.session.commit()


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_networking_model(user: UserClient):
    router = d.Router(speed=1000, wireless=True, owner_id=user.user['id'])
    db.session.add(router)
    switch = d.Switch(speed=1000, wireless=False, owner_id=user.user['id'])
    db.session.add(switch)
    db.session.commit()


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_cooking_mixer(user: UserClient):
    mixer = d.Mixer(serial_number='foo', model='bar', manufacturer='foobar',
                    owner_id=user.user['id'])
    db.session.add(mixer)
    db.session.commit()


def test_cooking_mixer_api(user: UserClient):
    snapshot, _ = user.post(
        {
            'type': 'Snapshot',
            'device': {
                'serialNumber': 'foo',
                'model': 'bar',
                'manufacturer': 'foobar',
                'type': 'Mixer'
            },
            'version': '11.0',
            'software': SnapshotSoftware.Web.name
        },
        res=m.Snapshot
    )
    mixer, _ = user.get(res=d.Device, item=snapshot['device']['id'])
    assert mixer['type'] == 'Mixer'
    assert mixer['serialNumber'] == 'foo'


@pytest.mark.mvp
def test_hid_with_mac(app: Devicehub, user: UserClient):
    """Checks hid with mac."""
    snapshot = file('asus-eee-1000h.snapshot.11')
    user.post(snapshot, res=m.Snapshot)
    pc, _ = user.get(res=d.Device, item=1)
    assert pc['hid'] == 'laptop-asustek_computer_inc-1000h-94oaaq021116-00:24:8c:7f:cf:2d'


@pytest.mark.mvp
def test_hid_without_mac(app: Devicehub, user: UserClient):
    """Checks hid without mac."""
    snapshot = file('asus-eee-1000h.snapshot.11')
    snapshot['components'] = [c for c in snapshot['components'] if c['type'] != 'NetworkAdapter']
    user.post(snapshot, res=m.Snapshot)
    pc, _ = user.get(res=d.Device, item=1)
    assert pc['hid'] == 'laptop-asustek_computer_inc-1000h-94oaaq021116'


@pytest.mark.mvp
def test_hid_with_mac_none(app: Devicehub, user: UserClient):
    """Checks hid with mac = None."""
    snapshot = file('asus-eee-1000h.snapshot.11')
    network = [c for c in snapshot['components'] if c['type'] == 'NetworkAdapter'][0]
    network['serialNumber'] = None
    user.post(snapshot, res=m.Snapshot)
    pc, _ = user.get(res=d.Device, item=1)
    assert pc['hid'] == 'laptop-asustek_computer_inc-1000h-94oaaq021116'


@pytest.mark.mvp
def test_hid_with_2networkadapters(app: Devicehub, user: UserClient):
    """Checks hid with 2 networks adapters"""
    snapshot = file('asus-eee-1000h.snapshot.11')
    network = [c for c in snapshot['components'] if c['type'] == 'NetworkAdapter'][0]
    network2 = copy.copy(network)
    snapshot['components'].append(network2)
    network['serialNumber'] = 'a0:24:8c:7f:cf:2d'
    user.post(snapshot, res=m.Snapshot)
    devices, _ = user.get(res=d.Device)

    laptop = devices['items'][0]
    assert laptop['hid'] == 'laptop-asustek_computer_inc-1000h-94oaaq021116-00:24:8c:7f:cf:2d'
    assert len([c for c in devices['items'] if c['type'] == 'Laptop']) == 1


@pytest.mark.mvp
def test_hid_with_2network_and_drop_no_mac_in_hid(app: Devicehub, user: UserClient):
    """Checks hid with 2 networks adapters and next drop the network is not used in hid"""
    snapshot = file('asus-eee-1000h.snapshot.11')
    network = [c for c in snapshot['components'] if c['type'] == 'NetworkAdapter'][0]
    network2 = copy.copy(network)
    snapshot['components'].append(network2)
    network['serialNumber'] = 'a0:24:8c:7f:cf:2d'
    user.post(snapshot, res=m.Snapshot)
    pc, _ = user.get(res=d.Device, item=1)
    assert pc['hid'] == 'laptop-asustek_computer_inc-1000h-94oaaq021116-00:24:8c:7f:cf:2d'

    snapshot['uuid'] = 'd1b70cb8-8929-4f36-99b7-fe052cec0abb'
    snapshot['components'] = [c for c in snapshot['components'] if c != network]
    user.post(snapshot, res=m.Snapshot)
    devices, _ = user.get(res=d.Device)
    laptop = devices['items'][0]
    assert laptop['hid'] == 'laptop-asustek_computer_inc-1000h-94oaaq021116-00:24:8c:7f:cf:2d'
    assert len([c for c in devices['items'] if c['type'] == 'Laptop']) == 1
    assert len([c for c in laptop['components'] if c['type'] == 'NetworkAdapter']) == 1


@pytest.mark.mvp
def test_hid_with_2network_and_drop_mac_in_hid(app: Devicehub, user: UserClient):
    """Checks hid with 2 networks adapters and next drop the network is used in hid"""
    # One tipical snapshot with 2 network cards
    snapshot = file('asus-eee-1000h.snapshot.11')
    network = [c for c in snapshot['components'] if c['type'] == 'NetworkAdapter'][0]
    network2 = copy.copy(network)
    snapshot['components'].append(network2)
    network['serialNumber'] = 'a0:24:8c:7f:cf:2d'
    user.post(snapshot, res=m.Snapshot)
    pc, _ = user.get(res=d.Device, item=1)
    assert pc['hid'] == 'laptop-asustek_computer_inc-1000h-94oaaq021116-00:24:8c:7f:cf:2d'

    # we drop the network card then is used for to build the hid
    snapshot['uuid'] = 'd1b70cb8-8929-4f36-99b7-fe052cec0abb'
    snapshot['components'] = [c for c in snapshot['components'] if c != network2]
    user.post(snapshot, res=m.Snapshot)
    devices, _ = user.get(res=d.Device)
    laptops = [c for c in devices['items'] if c['type'] == 'Laptop']
    assert len(laptops) == 2
    hids = [h['hid'] for h in laptops]
    proof_hid = ['laptop-asustek_computer_inc-1000h-94oaaq021116-a0:24:8c:7f:cf:2d',
                 'laptop-asustek_computer_inc-1000h-94oaaq021116-00:24:8c:7f:cf:2d']
    assert all([h in proof_hid for h in hids])

    # we drop all network cards
    snapshot['uuid'] = 'd1b70cb8-8929-4f36-99b7-fe052cec0abc'
    snapshot['components'] = [c for c in snapshot['components'] if not c in [network, network2]]
    user.post(snapshot, res=m.Snapshot)
    devices, _ = user.get(res=d.Device)
    laptops = [c for c in devices['items'] if c['type'] == 'Laptop']
    assert len(laptops) == 3
    hids = [h['hid'] for h in laptops]
    proof_hid = ['laptop-asustek_computer_inc-1000h-94oaaq021116-a0:24:8c:7f:cf:2d',
                 'laptop-asustek_computer_inc-1000h-94oaaq021116-00:24:8c:7f:cf:2d',
                 'laptop-asustek_computer_inc-1000h-94oaaq021116']
    assert all([h in proof_hid for h in hids])

