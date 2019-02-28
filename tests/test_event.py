import ipaddress
from datetime import timedelta
from decimal import Decimal
from typing import Tuple

import pytest
from flask import current_app as app, g
from sqlalchemy.util import OrderedSet
from teal.enums import Currency, Subdivision

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.resources import enums
from ereuse_devicehub.resources.device import states
from ereuse_devicehub.resources.device.models import Desktop, Device, GraphicCard, HardDrive, \
    RamModule, SolidStateDrive
from ereuse_devicehub.resources.enums import ComputerChassis, Severity, TestDataStorageLength
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
        steps=[
            models.StepZero(**conftest.T),
            models.StepRandom(**conftest.T)
        ],
        **conftest.T
    )
    db.session.add(erasure)
    db.session.commit()
    db_erasure = models.EraseBasic.query.one()
    assert erasure == db_erasure
    assert next(iter(db_erasure.device.events)) == erasure
    assert not erasure.standards, 'EraseBasic themselves do not have standards'


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
def test_erase_sectors_steps_erasure_standards_hmg_is5():
    erasure = models.EraseSectors(
        device=SolidStateDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        steps=[
            models.StepZero(**conftest.T),
            models.StepRandom(**conftest.T),
            models.StepRandom(**conftest.T)
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
    assert {enums.ErasureStandards.HMG_IS5} == erasure.standards


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_test_data_storage_working():
    """Tests TestDataStorage with the resulting properties in Device."""
    hdd = HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar')
    test = models.TestDataStorage(
        device=hdd,
        severity=Severity.Error,
        elapsed=timedelta(minutes=25),
        length=TestDataStorageLength.Short,
        status=':-(',
        lifetime=timedelta(days=120)
    )
    db.session.add(test)
    db.session.flush()
    assert hdd.working == [test]
    assert not hdd.problems
    # Add new test overriding the first test in the problems
    # / working condition
    test2 = models.TestDataStorage(
        device=hdd,
        severity=Severity.Warning,
        elapsed=timedelta(minutes=25),
        length=TestDataStorageLength.Short,
        status=':-(',
        lifetime=timedelta(days=120)
    )
    db.session.add(test2)
    db.session.flush()
    assert hdd.working == [test2]
    assert hdd.problems == []


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
    computer = Desktop(serial_number='sn1',
                       model='ml1',
                       manufacturer='mr1',
                       chassis=ComputerChassis.Tower)
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
    computer = Desktop(serial_number='sn1',
                       model='ml1',
                       manufacturer='mr1',
                       chassis=ComputerChassis.Tower)
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
    computer = Desktop(serial_number='sn1',
                       model='ml1',
                       manufacturer='mr1',
                       chassis=ComputerChassis.Tower)
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


@pytest.mark.parametrize('event_model_state', [
    (models.ToRepair, states.Physical.ToBeRepaired),
    (models.Repair, states.Physical.Repaired),
    (models.ToPrepare, states.Physical.Preparing),
    (models.ReadyToUse, states.Physical.ReadyToBeUsed),
    (models.Prepare, states.Physical.Prepared)
])
def test_generic_event(event_model_state: Tuple[models.Event, states.Trading], user: UserClient):
    """Tests POSTing all generic events."""
    event_model, state = event_model_state
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    event = {'type': event_model.t, 'devices': [snapshot['device']['id']]}
    event, _ = user.post(event, res=models.Event)
    assert event['devices'][0]['id'] == snapshot['device']['id']
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert device['events'][-1]['id'] == event['id']
    assert device['physical'] == state.name


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_live():
    """Tests inserting a Live into the database and GETting it."""
    db_live = models.Live(ip=ipaddress.ip_address('79.147.10.10'),
                          subdivision_confidence=84,
                          subdivision=Subdivision['ES-CA'],
                          city='barcelona',
                          city_confidence=20,
                          isp='acme',
                          device=Desktop(serial_number='sn1', model='ml1', manufacturer='mr1',
                                         chassis=ComputerChassis.Docking),
                          organization='acme1',
                          organization_type='acme1bis')
    db.session.add(db_live)
    db.session.commit()
    client = UserClient(app, 'foo@foo.com', 'foo', response_wrapper=app.response_class)
    client.login()
    live, _ = client.get(res=models.Event, item=str(db_live.id))
    assert live['ip'] == '79.147.10.10'
    assert live['subdivision'] == 'ES-CA'
    assert live['country'] == 'ES'
    device, _ = client.get(res=Device, item=live['device']['id'])
    assert device['physical'] == states.Physical.InUse.name


@pytest.mark.xfail(reson='Functionality not developed.')
def test_live_geoip():
    """Tests performing a Live action using the GEOIP library."""


@pytest.mark.xfail(reson='Develop reserve')
def test_reserve_and_cancel(user: UserClient):
    """Performs a reservation and then cancels it,
    checking the attribute `reservees`.
    """


@pytest.mark.parametrize('event_model_state', [
    (models.Sell, states.Trading.Sold),
    (models.Donate, states.Trading.Donated),
    (models.Rent, states.Trading.Renting),
    (models.DisposeProduct, states.Trading.ProductDisposed)
])
def test_trade(event_model_state: Tuple[models.Event, states.Trading], user: UserClient):
    """Tests POSTing all Trade events."""
    event_model, state = event_model_state
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
    assert device['trading'] == state.name


@pytest.mark.xfail(reson='Develop migrate')
def test_migrate():
    pass


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_price_custom():
    computer = Desktop(serial_number='sn1', model='ml1', manufacturer='mr1',
                       chassis=ComputerChassis.Docking)
    price = models.Price(price=Decimal(25.25), currency=Currency.EUR)
    price.device = computer
    assert computer.price == price
    db.session.add(computer)
    db.session.commit()

    client = UserClient(app, 'foo@foo.com', 'foo', response_wrapper=app.response_class)
    client.login()
    p, _ = client.get(res=models.Event, item=str(price.id))
    assert p['device']['id'] == price.device.id == computer.id
    assert p['price'] == 25.25
    assert p['currency'] == Currency.EUR.name == 'EUR'

    c, _ = client.get(res=Device, item=computer.id)
    assert c['price']['id'] == p['id']


def test_price_custom_client(user: UserClient):
    """As test_price_custom but creating the price through the API."""
    s = file('basic.snapshot')
    snapshot, _ = user.post(s, res=models.Snapshot)
    price, _ = user.post({
        'type': 'Price',
        'price': 25,
        'currency': Currency.EUR.name,
        'device': snapshot['device']['id']
    }, res=models.Event)
    assert 25 == price['price']
    assert Currency.EUR.name == price['currency']

    device, _ = user.get(res=Device, item=price['device']['id'])
    assert 25 == device['price']['price']


@pytest.mark.xfail(reson='Develop test')
def test_ereuse_price():
    """Tests the several ways of creating eReuse Price, emulating
    from an AggregateRate and ensuring that the different Range
    return correct results."""
    # important to check Range.low no returning warranty2
    # Range.verylow not returning nothing


@pytest.mark.usefixtures(conftest.auth_app_context.__name__)
def test_erase_physical():
    erasure = models.ErasePhysical(
        device=HardDrive(serial_number='foo', manufacturer='bar', model='foo-bar'),
        method=enums.PhysicalErasureMethod.Disintegration
    )
    db.session.add(erasure)
    db.session.commit()


@pytest.mark.xfail(reson='Adapt rate algorithm to re-compute by passing a manual rate.')
def test_manual_rate_after_workbench_rate(user: UserClient):
    """Perform a WorkbenchRate and then update the device with a ManualRate.

    Devicehub must make the final rate with the first workbench rate
    plus the new manual rate, without considering the appearance /
    functionality values of the workbench rate.
    """
    s = file('real-hp.snapshot.11')
    snapshot, _ = user.post(s, res=models.Snapshot)
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert 'B' == device['rate']['appearanceRange']
    assert device['rate'] == 1
    user.post({
        'type': 'ManualRate',
        'device': device['id'],
        'appearanceRange': 'A',
        'functionalityRange': 'A'
    }, res=models.Event)
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert 'A' == device['rate']['appearanceRange']


@pytest.mark.xfail(reson='Develop an algorithm that can make rates only from manual rates')
def test_manual_rate_without_workbench_rate(user: UserClient):
    pass
