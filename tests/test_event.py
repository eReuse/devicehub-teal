import ipaddress
from datetime import timedelta

import pytest
from flask import current_app as app, g
from sqlalchemy.util import OrderedSet
from teal.enums import Currency, Subdivision

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Desktop, Device, GraphicCard, HardDrive, \
    RamModule, SolidStateDrive
from ereuse_devicehub.resources.enums import ComputerChassis, TestHardDriveLength
from ereuse_devicehub.resources.event import models
from tests import conftest
from tests.conftest import create_user, file


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_author():
    """
    Checks the default created author.

    Note that the author can be accessed after inserting the row.
    """
    user = create_user()
    g.user = user
    e = models.EventWithOneDevice(device=Device())
    db.session.add(e)
    assert e.author is None
    assert e.author_id is None
    db.session.commit()
    assert e.author == user


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_erase_basic():
    erasure = models.EraseBasic(
        device=HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        zeros=True,
        **conftest.T
    )
    db.session.add(erasure)
    db.session.commit()
    db_erasure = models.EraseBasic.query.one()
    assert erasure == db_erasure
    assert next(iter(db_erasure.device.events)) == erasure


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_validate_device_data_storage():
    """Checks the validation for data-storage-only events works."""
    # We can't set a GraphicCard
    with pytest.raises(TypeError,
                       message='EraseBasic.device must be a DataStorage '
                               'but you passed <GraphicCard None model=\'foo-bar\' S/N=\'foo\'>'):
        models.EraseBasic(
            device=GraphicCard(serial_number='foo', manufacturer='bar', model='foo-bar'),
            clean_with_zeros=True,
            **conftest.T
        )


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_erase_sectors_steps():
    erasure = models.EraseSectors(
        device=SolidStateDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        zeros=True,
        steps=[
            models.StepZero(**conftest.T),
            models.StepRandom(**conftest.T),
            models.StepZero(**conftest.T)
        ],
        **conftest.T
    )
    db.session.add(erasure)
    db.session.commit()
    db_erasure = models.EraseSectors.query.one()
    # Steps are in order
    assert db_erasure.steps[0].num == 0
    assert db_erasure.steps[1].num == 1
    assert db_erasure.steps[2].num == 2


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_test_data_storage():
    test = models.TestDataStorage(
        device=HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        error=False,
        elapsed=timedelta(minutes=25),
        length=TestHardDriveLength.Short,
        status='OK!',
        lifetime=timedelta(days=120)
    )
    db.session.add(test)
    db.session.commit()
    assert models.TestDataStorage.query.one()


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_install():
    hdd = HardDrive(serial_number='sn')
    install = models.Install(name='LinuxMint 18.04 es',
                             elapsed=timedelta(seconds=25),
                             device=hdd)
    db.session.add(install)
    db.session.commit()


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_update_components_event_one():
    computer = Desktop(serial_number='sn1', model='ml1', manufacturer='mr1')
    hdd = HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar')
    computer.components.add(hdd)

    # Add event
    test = models.StressTest(elapsed=timedelta(seconds=1))
    computer.events_one.add(test)
    assert test.device == computer
    assert next(iter(test.components)) == hdd, 'Event has to have new components'

    # Remove event
    computer.events_one.clear()
    assert not test.device
    assert not test.components, 'Event has to loose the components'

    # If we add a component to a device AFTER assigning the event
    # to the device, the event doesn't get the new component
    computer.events_one.add(test)
    ram = RamModule()
    computer.components.add(ram)
    assert len(test.components) == 1


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_update_components_event_multiple():
    computer = Desktop(serial_number='sn1', model='ml1', manufacturer='mr1')
    hdd = HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar')
    computer.components.add(hdd)

    ready = models.ReadyToUse()
    assert not ready.devices
    assert not ready.components

    # Add
    computer.events_multiple.add(ready)
    assert ready.devices == OrderedSet([computer])
    assert next(iter(ready.components)) == hdd

    # Remove
    computer.events_multiple.remove(ready)
    assert not ready.devices
    assert not ready.components

    # init / replace collection
    ready.devices = OrderedSet([computer])
    assert ready.devices
    assert ready.components


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_update_parent():
    computer = Desktop(serial_number='sn1', model='ml1', manufacturer='mr1')
    hdd = HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar')
    computer.components.add(hdd)

    # Add
    benchmark = models.BenchmarkDataStorage()
    benchmark.device = hdd
    assert benchmark.parent == computer
    assert not benchmark.components

    # Remove
    benchmark.device = None
    assert not benchmark.parent


@pytest.mark.parametrize('event_model', [
    models.ToRepair,
    models.Repair,
    models.ToPrepare,
    models.ReadyToUse,
    models.ToPrepare,
    models.Prepare,
])
def test_generic_event(event_model: models.Event, user: UserClient):
    """Tests POSTing all generic events."""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    event = {'type': event_model.t, 'devices': [snapshot['device']['id']]}
    event, _ = user.post(event, res=models.Event)
    assert event['devices'][0]['id'] == snapshot['device']['id']
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert device['events'][-1]['id'] == event['id']


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_live():
    """Tests inserting a Live into the database and GETting it."""
    db_live = models.Live(ip=ipaddress.ip_address('79.147.10.10'),
                          subdivision_confidence=84,
                          subdivision=Subdivision['ES-CA'],
                          city='Barcelona',
                          city_confidence=20,
                          isp='ACME',
                          device=Desktop(serial_number='sn1', model='ml1', manufacturer='mr1',
                                         chassis=ComputerChassis.Docking),
                          organization='ACME1',
                          organization_type='ACME1bis')
    db.session.add(db_live)
    db.session.commit()
    client = UserClient(app, 'foo@foo.com', 'foo', response_wrapper=app.response_class)
    client.login()
    live, _ = client.get(res=models.Event, item=str(db_live.id))
    assert live['ip'] == '79.147.10.10'
    assert live['subdivision'] == 'ES-CA'
    assert live['country'] == 'ES'


@pytest.mark.xfail(reson='Functionality not developed.')
def test_live_geoip():
    """Tests performing a Live action using the GEOIP library."""


@pytest.mark.xfail(reson='Develop reserve')
def test_reserve(user: UserClient):
    """Performs a reservation and then cancels it."""


@pytest.mark.parametrize('event_model', [
    models.Sell,
    models.Donate,
    models.Rent,
    models.DisposeProduct
])
def test_trade(event_model: models.Event, user: UserClient):
    """Tests POSTing all generic events."""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    event = {
        'type': event_model.t,
        'devices': [snapshot['device']['id']],
        'to': user.user['individuals'][0]['id'],
        'shippingDate': '2018-06-29T12:28:54',
        'invoiceNumber': 'ABC'
    }
    event, _ = user.post(event, res=models.Event)
    assert event['devices'][0]['id'] == snapshot['device']['id']
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert device['events'][-1]['id'] == event['id']


@pytest.mark.xfail(reson='Develop migrate')
def test_migrate():
    pass


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_price_custom():
    computer = Desktop(serial_number='sn1', model='ml1', manufacturer='mr1',
                       chassis=ComputerChassis.Docking)
    price = models.Price(price=25.25, currency=Currency.EUR)
    price.device = computer
    db.session.add(computer)
    db.session.commit()

    client = UserClient(app, 'foo@foo.com', 'foo', response_wrapper=app.response_class)
    client.login()
    p, _ = client.get(res=models.Event, item=str(price.id))
    assert p['device']['id'] == price.device.id == computer.id
    assert p['price'] == 25.25
    assert p['currency'] == Currency.EUR.name == 'EUR'
