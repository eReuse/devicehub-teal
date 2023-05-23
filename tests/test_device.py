import datetime
from uuid import UUID

import pytest
from colour import Color
from flask import g
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.ereuse_utils.test import ANY
from ereuse_devicehub.resources.action import models as m
from ereuse_devicehub.resources.action.models import Remove, TestConnectivity
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.device import models as d
from ereuse_devicehub.resources.device.schemas import Device as DeviceS
from ereuse_devicehub.resources.device.sync import Sync
from ereuse_devicehub.resources.enums import (
    ComputerChassis,
    DisplayTech,
    Severity,
    SnapshotSoftware,
    TransferState,
)
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.resources.user import User
from ereuse_devicehub.teal.enums import Layouts
from tests import conftest
from tests.conftest import file, yaml2json


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_device_model():
    """Tests that the correctness of the device model and its relationships."""
    pc = d.Desktop(
        model='p1mo',
        manufacturer='p1ma',
        serial_number='p1s',
        chassis=ComputerChassis.Tower,
    )
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
    pc = d.Device.query.filter_by(
        id=pc.id
    ).first()  # this is the same as querying for d.Desktop directly
    assert pc.components == {graphic}
    network_adapter = d.NetworkAdapter.query.one()
    assert network_adapter not in pc.components
    assert network_adapter.parent is None

    # Deleting the pc deletes everything
    gcard = d.GraphicCard.query.one()
    db.session.delete(pc)
    db.session.flush()
    assert pc.id == 3
    assert d.Desktop.query.first() is None
    db.session.commit()
    assert d.Desktop.query.first() is None
    assert network_adapter.id == 4
    assert d.NetworkAdapter.query.first() is not None, 'We removed the network adaptor'
    assert gcard.id == 5, 'We should still hold a reference to a zombie graphic card'
    assert (
        d.GraphicCard.query.first() is None
    ), 'We should have deleted it –it was inside the pc'


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
    c = d.Motherboard(
        slots=2,
        usb=3,
        serial_number='sn',
        model='ml',
        manufacturer='mr',
        width=2.0,
        color=Color(),
    )
    pc = d.Desktop(
        chassis=ComputerChassis.Tower,
        model='foo',
        manufacturer='bar',
        serial_number='foo-bar',
        weight=2.8,
        width=1.4,
        height=2.1,
        color=Color('LightSeaGreen'),
    )
    pc.components.add(c)
    db.session.add(pc)
    db.session.commit()
    assert c.physical_properties == {
        'usb': 3,
        'serial_number': 'sn',
        'part_number': None,
        'pcmcia': None,
        'model': 'ml',
        'slots': 2,
        'serial': None,
        'firewire': None,
        'manufacturer': 'mr',
        'bios_date': None,
        'ram_max_size': None,
        'ram_slots': None,
    }
    assert pc.physical_properties == {
        'amount': 0,
        'manufacturer': 'bar',
        'model': 'foo',
        'serial_number': 'foo-bar',
        'part_number': None,
    }


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_add_remove():
    # Original state:
    # pc has c1 and c2
    # pc2 has c3
    # c4 is not with any pc
    user = User.query.filter().first()
    values = yaml2json('pc-components.db')
    pc = values['device']
    c1, c2 = (d.Component(**c) for c in values['components'])
    pc = d.Desktop(**pc, components=OrderedSet([c1, c2]))
    db.session.add(pc)
    c3 = d.Component(serial_number='nc1', owner_id=user.id)
    pc2 = d.Desktop(
        serial_number='s2',
        components=OrderedSet([c3]),
        chassis=ComputerChassis.Microtower,
    )
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
    s = yaml2json('pc-components.db')
    pc = d.Desktop(
        **s['device'], components=OrderedSet(d.Component(**c) for c in s['components'])
    )
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
    s = yaml2json('pc-components.db')
    pc = d.Desktop(
        **s['device'], components=OrderedSet(d.Component(**c) for c in s['components'])
    )
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
    pc = d.Desktop(**yaml2json('pc-components.db')['device'])
    db_pc = Sync().execute_register(pc)
    assert pc.physical_properties == db_pc.physical_properties


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_sync_execute_register_desktop_existing_no_tag():
    """Syncs an existing d.Desktop with HID and without a tag."""
    pc = d.Desktop(**yaml2json('pc-components.db')['device'])
    db.session.add(pc)
    db.session.commit()

    pc = d.Desktop(
        **yaml2json('pc-components.db')['device']
    )  # Create a new transient non-db object
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
    device = yaml2json('pc-components.db')['device']
    device['owner_id'] = user.user['id']
    pc = d.Desktop(**device)
    # 1: device has no HID
    pc.hid = pc.model = None
    returned_pc = Sync().execute_register(pc)
    assert returned_pc == pc


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_sync_execute_register_tag_linked_same_device():
    """If the tag is linked to the device, regardless if it has HID,
    the system should match the device through the tag.
    (If it has HID it validates both HID and tag point at the same
    device, this his checked in ).
    """
    orig_pc = d.Desktop(**yaml2json('pc-components.db')['device'])
    db.session.add(Tag(id='foo', device=orig_pc))
    db.session.commit()

    pc = d.Desktop(
        **yaml2json('pc-components.db')['device']
    )  # Create a new transient non-db object
    pc.tags.add(Tag(id='foo'))
    db_pc = Sync().execute_register(pc)
    assert db_pc.id == orig_pc.id
    assert len(db_pc.tags) == 1
    for tag in db_pc.tags:
        assert tag.id in ['foo', db_pc.devicehub_id]


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_get_device(user: UserClient):
    """Checks GETting a d.Desktop with its components."""
    g.user = User.query.one()
    pc = d.Desktop(
        model='p1mo',
        manufacturer='p1ma',
        serial_number='p1s',
        chassis=ComputerChassis.Tower,
        owner_id=user.user['id'],
    )
    pc.components = OrderedSet(
        [
            d.NetworkAdapter(
                model='c1mo',
                manufacturer='c1ma',
                serial_number='c1s',
                owner_id=user.user['id'],
            ),
            d.GraphicCard(
                model='c2mo', manufacturer='c2ma', memory=1500, owner_id=user.user['id']
            ),
        ]
    )
    db.session.add(pc)
    # todo test is an abstract class. replace with another one
    db.session.add(
        TestConnectivity(
            device=pc,
            severity=Severity.Info,
            agent=Person(name='Timmy'),
            author=User(email='bar@bar.com'),
        )
    )
    db.session.commit()
    pc_api, _ = user.get(res=d.Device, item=pc.devicehub_id)
    assert len(pc_api['actions']) == 1
    assert pc_api['actions'][0]['type'] == 'TestConnectivity'
    assert pc_api['actions'][0]['device'] == pc.id
    assert pc_api['actions'][0]['severity'] == 'Info'
    assert UUID(pc_api['actions'][0]['author'])
    assert (
        'actions_components' not in pc_api
    ), 'actions_components are internal use only'
    assert 'actions_one' not in pc_api, 'they are internal use only'
    assert 'author' not in pc_api
    assert tuple(c['id'] for c in pc_api['components']) == tuple(
        c.id for c in pc.components
    )
    assert pc_api['hid'] == 'desktop-p1ma-p1mo-p1s'
    assert pc_api['model'] == 'p1mo'
    assert pc_api['manufacturer'] == 'p1ma'
    assert pc_api['serialNumber'] == 'p1s'
    assert pc_api['type'] == d.Desktop.t


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_get_devices(app: Devicehub, user: UserClient):
    """Checks GETting multiple devices."""
    g.user = User.query.one()
    pc = d.Desktop(
        model='p1mo',
        manufacturer='p1ma',
        serial_number='p1s',
        chassis=ComputerChassis.Tower,
        owner_id=user.user['id'],
    )
    pc.components = OrderedSet(
        [
            d.NetworkAdapter(
                model='c1mo',
                manufacturer='c1ma',
                serial_number='c1s',
                owner_id=user.user['id'],
            ),
            d.GraphicCard(
                model='c2mo', manufacturer='c2ma', memory=1500, owner_id=user.user['id']
            ),
        ]
    )
    pc1 = d.Desktop(
        model='p2mo',
        manufacturer='p2ma',
        serial_number='p2s',
        chassis=ComputerChassis.Tower,
        owner_id=user.user['id'],
    )
    pc2 = d.Laptop(
        model='p3mo',
        manufacturer='p3ma',
        serial_number='p3s',
        chassis=ComputerChassis.Netbook,
        owner_id=user.user['id'],
    )
    db.session.add_all((pc, pc1, pc2))
    db.session.commit()
    devices, _ = user.get(res=d.Device)
    ids = (pc.id, pc1.id, pc2.id, pc.components[0].id, pc.components[1].id)
    assert tuple(dev['id'] for dev in devices['items']) == ids
    assert tuple(dev['type'] for dev in devices['items']) == (
        d.Desktop.t,
        d.Desktop.t,
        d.Laptop.t,
        d.NetworkAdapter.t,
        d.GraphicCard.t,
    )


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_get_device_permissions(
    app: Devicehub, user: UserClient, user2: UserClient, client: Client
):
    """Checks GETting a d.Desktop with its components."""

    s, _ = user.post(file('asus-eee-1000h.snapshot.11'), res=m.Snapshot)
    pc, res = user.get(res=d.Device, item=s['device']['devicehubID'])
    assert res.status_code == 200
    assert len(pc['actions']) == 0
    pc = d.Device.query.filter_by(devicehub_id=s['device']['devicehubID']).one()
    assert len(pc.placeholder.binding.actions) == 7

    html, _ = client.get(res=d.Device, item=s['device']['devicehubID'], accept=ANY)
    assert 'intel atom cpu n270 @ 1.60ghz' in html
    pc2, res2 = user2.get(res=d.Device, item=s['device']['devicehubID'], accept=ANY)
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
    assert len(devices['items']) == 2
    assert len(devices2['items']) == 0


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_get_devices_unassigned(user: UserClient):
    """Checks GETting multiple devices."""

    user.post(file('asus-eee-1000h.snapshot.11'), res=m.Snapshot)
    url = '/devices/?filter={"type":["Computer"]}&unassign=0'

    devices, res = user.get(url, None)
    assert res.status_code == 200
    assert len(devices['items']) == 2

    url = '/devices/?filter={"type":["Computer"]}&unassign=1'

    devices, res = user.get(url, None)
    assert res.status_code == 200
    assert len(devices['items']) == 2

    from ereuse_devicehub.resources.lot.models import Lot

    device_id = devices['items'][0]['id']
    my_lot, _ = user.post(({'name': 'My_lot'}), res=Lot)
    lot, _ = user.post(
        {}, res=Lot, item='{}/devices'.format(my_lot['id']), query=[('id', device_id)]
    )
    lot = Lot.query.filter_by(id=lot['id']).one()
    assert next(iter(lot.devices)).id == device_id

    url = '/devices/?filter={"type":["Computer"]}&unassign=0'

    devices, res = user.get(url, None)
    assert res.status_code == 200
    assert len(devices['items']) == 2

    url = '/devices/?filter={"type":["Computer"]}&unassign=1'

    devices, res = user.get(url, None)
    assert res.status_code == 200
    assert len(devices['items']) == 1


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_computer_monitor():
    m = d.ComputerMonitor(
        technology=DisplayTech.LCD,
        manufacturer='foo',
        model='bar',
        serial_number='foo-bar',
        resolution_width=1920,
        resolution_height=1080,
        size=14.5,
    )
    db.session.add(m)
    db.session.commit()


@pytest.mark.mvp
def test_manufacturer(user: UserClient):
    m, r = user.get(res='Manufacturer', query=[('search', 'asus')])
    assert m == {
        'items': [{'name': 'Asus', 'url': 'https://en.wikipedia.org/wiki/Asus'}]
    }
    assert r.cache_control.public
    assert r.expires.timestamp() > datetime.datetime.now().timestamp()


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
        pc = d.Laptop.query.filter_by(placeholder=None).one()  # type: d.Laptop
        assert format(pc) == 'Laptop 3: model 1000h, S/N 94oaaq021116'
        assert format(pc, 't') == 'Netbook 1000h'
        assert format(pc, 's') == '(asustek computer inc.) S/N 94OAAQ021116'
        assert pc.ram_size == 1024
        assert pc.data_storage_size == 152627
        assert (
            pc.graphic_card_model
            == 'mobile 945gse express integrated graphics controller'
        )
        assert pc.processor_model == 'intel atom cpu n270 @ 1.60ghz'
        net = next(c for c in pc.components if isinstance(c, d.NetworkAdapter))
        assert (
            format(net) == 'NetworkAdapter 5: model ar8121/ar8113/ar8114 '
            'gigabit or fast ethernet, S/N 00:24:8c:7f:cf:2d'
        )
        assert (
            format(net, 't')
            == 'NetworkAdapter ar8121/ar8113/ar8114 gigabit or fast ethernet'
        )
        assert format(net, 's') == 'qualcomm atheros 00:24:8C:7F:CF:2D – 100 Mbps'
        hdd = next(c for c in pc.components if isinstance(c, d.DataStorage))
        assert format(hdd) == 'HardDrive 10: model st9160310as, S/N 5sv4tqa6'
        assert format(hdd, 't') == 'HardDrive st9160310as'
        assert format(hdd, 's') == 'seagate 5SV4TQA6 – 152 GB'


@pytest.mark.mvp
def test_device_public(user: UserClient, client: Client):
    s, _ = user.post(file('asus-eee-1000h.snapshot.11'), res=m.Snapshot)
    html, _ = client.get(res=d.Device, item=s['device']['devicehubID'], accept=ANY)
    assert 'intel atom cpu n270 @ 1.60ghz' in html


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_computer_accessory_model(user: UserClient):
    g.user = User.query.one()
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
    g.user = User.query.one()
    router = d.Router(speed=1000, wireless=True, owner_id=user.user['id'])
    db.session.add(router)
    switch = d.Switch(speed=1000, wireless=False, owner_id=user.user['id'])
    db.session.add(switch)
    db.session.commit()


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_cooking_mixer(user: UserClient):
    mixer = d.Mixer(
        serial_number='foo',
        model='bar',
        manufacturer='foobar',
        owner_id=user.user['id'],
    )
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
                'type': 'Mixer',
            },
            'version': '11.0',
            'software': SnapshotSoftware.Web.name,
        },
        res=m.Snapshot,
    )
    mixer, _ = user.get(res=d.Device, item=snapshot['device']['id'])
    assert mixer['type'] == 'Mixer'
    assert mixer['serialNumber'] == 'foo'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_hid_with_placeholder(app: Devicehub, user: UserClient):
    """Checks hid with mac."""
    snapshot = file('asus-eee-1000h.snapshot.11')
    snap, _ = user.post(snapshot, res=m.Snapshot)
    pc, _ = user.get(res=d.Device, item=snap['device']['devicehubID'])
    pc = d.Device.query.filter_by(devicehub_id=snap['device']['devicehubID']).one()
    assert pc.placeholder.binding.hid == pc.hid
