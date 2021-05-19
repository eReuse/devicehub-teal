import os
import base64
import ipaddress
import json
import shutil
import copy
import pytest

from datetime import datetime, timedelta
from dateutil.tz import tzutc
from decimal import Decimal
from typing import Tuple, Type
from pytest import raises
from json.decoder import JSONDecodeError

from flask import current_app as app, g
from sqlalchemy.util import OrderedSet
from teal.enums import Currency, Subdivision

from ereuse_devicehub.db import db
from ereuse_devicehub.client import UserClient, Client
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources import enums
from ereuse_devicehub.resources.hash_reports import ReportHash 
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.action import models
from ereuse_devicehub.resources.device import states
from ereuse_devicehub.resources.device.models import Desktop, Device, GraphicCard, HardDrive, \
    RamModule, SolidStateDrive
from ereuse_devicehub.resources.enums import ComputerChassis, Severity, TestDataStorageLength
from ereuse_devicehub.resources.tradedocument.models import TradeDocument

from tests import conftest
from tests.conftest import create_user, file



@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_offer_without_to(user: UserClient):
    """Test one offer with automatic confirmation and without user to"""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device = Device.query.filter_by(id=snapshot['device']['id']).one()
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    user.post({},
              res=Lot,
              item='{}/devices'.format(lot['id']),
              query=[('id', device.id)])

    # check the owner of the device
    assert device.owner.email == user.email
    for c in device.components:
        assert c.owner.email == user.email

    request_post = {
        'type': 'Trade',
        'devices': [device.id],
        'userFrom': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirm': False,
        'code': 'MAX'
    }
    user.post(res=models.Action, data=request_post)

    trade = models.Trade.query.one()
    assert device in trade.devices
    # assert trade.confirm_transfer
    users = [ac.user for ac in trade.acceptances]
    assert trade.user_to == device.owner
    assert request_post['code'].lower() in device.owner.email
    assert device.owner.active == False
    assert device.owner.phantom == True
    assert trade.user_to in users
    assert trade.user_from in users
    assert device.owner.email != user.email
    for c in device.components:
        assert c.owner.email != user.email

    # check if the user_from is owner of the devices
    request_post = {
        'type': 'Trade',
        'devices': [device.id],
        'userFrom': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirm': False,
        'code': 'MAX'
    }
    user.post(res=models.Action, data=request_post, status=422)
    trade = models.Trade.query.one()

    # Check if the new phantom account is reused and not duplicated
    computer = file('1-device-with-components.snapshot')
    snapshot2, _ = user.post(computer, res=models.Snapshot)
    device2 = Device.query.filter_by(id=snapshot2['device']['id']).one()
    lot2 = Lot('MyLot2')
    lot2.owner_id = user.user['id']
    lot2.devices.add(device2)
    db.session.add(lot2)
    db.session.flush()
    request_post2 = {
        'type': 'Trade',
        'devices': [device2.id],
        'userFrom': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot2.id,
        'confirm': False,
        'code': 'MAX'
    }
    user.post(res=models.Action, data=request_post2)
    assert User.query.filter_by(email=device.owner.email).count() == 1


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_offer_without_from(user: UserClient, user2: UserClient):
    """Test one offer without confirmation and without user from"""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    lot = Lot('MyLot')
    lot.owner_id = user.user['id']
    device = Device.query.filter_by(id=snapshot['device']['id']).one()

    # check the owner of the device
    assert device.owner.email == user.email
    assert device.owner.email != user2.email

    lot.devices.add(device)
    db.session.add(lot)
    db.session.flush()
    request_post = {
        'type': 'Trade',
        'devices': [device.id],
        'userTo': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot.id,
        'confirm': False,
        'code': 'MAX'
    }
    action, _ = user2.post(res=models.Action, data=request_post, status=422)

    request_post['userTo'] = user.email
    action, _ = user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    phantom_user = trade.user_from
    assert request_post['code'].lower() in phantom_user.email
    assert phantom_user.active == False
    assert phantom_user.phantom == True
    # assert trade.confirm_transfer

    users = [ac.user for ac in trade.acceptances]
    assert trade.user_to in users
    assert trade.user_from in users
    assert user.email in trade.devices[0].owner.email
    assert device.owner.email != user2.email
    assert device.owner.email == user.email


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_offer_without_users(user: UserClient):
    """Test one offer with doble confirmation"""
    user2 = User(email='baz@baz.cxm', password='baz')
    user2.individuals.add(Person(name='Tommy'))
    db.session.add(user2)
    db.session.commit()
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    lot = Lot('MyLot')
    lot.owner_id = user.user['id']
    device = Device.query.filter_by(id=snapshot['device']['id']).one()
    lot.devices.add(device)
    db.session.add(lot)
    db.session.flush()
    request_post = {
        'type': 'Trade',
        'devices': [device.id],
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot.id,
        'confirm': False,
        'code': 'MAX'
    }
    action, response = user.post(res=models.Action, data=request_post, status=422)
    txt = 'you need one user from or user to for to do a offer'
    assert txt in action['message']['_schema']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_offer(user: UserClient):
    """Test one offer with doble confirmation"""
    user2 = User(email='baz@baz.cxm', password='baz')
    user2.individuals.add(Person(name='Tommy'))
    db.session.add(user2)
    db.session.commit()
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    lot = Lot('MyLot')
    lot.owner_id = user.user['id']
    device = Device.query.filter_by(id=snapshot['device']['id']).one()
    assert device.owner.email == user.email
    assert device.owner.email != user2.email
    lot.devices.add(device)
    db.session.add(lot)
    db.session.flush()
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFrom': user.email,
        'userTo': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot.id,
        'confirm': True,
    }

    action, _ = user.post(res=models.Action, data=request_post)
    # no there are transfer of devices
    assert device.owner.email == user.email
    assert device.owner.email != user2.email


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_offer_without_devices(user: UserClient):
    """Test one offer with doble confirmation"""
    user2 = User(email='baz@baz.cxm', password='baz')
    user2.individuals.add(Person(name='Tommy'))
    db.session.add(user2)
    db.session.commit()
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFrom': user.email,
        'userTo': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirm': True,
    }

    user.post(res=models.Action, data=request_post)
    # no there are transfer of devices


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_endpoint_confirm(user: UserClient, user2: UserClient):
    """Check the normal creation and visualization of one confirmation trade"""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device_id = snapshot['device']['id']
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    user.post({},
              res=Lot,
              item='{}/devices'.format(lot['id']),
              query=[('id', device_id)])

    request_post = {
        'type': 'Trade',
        'devices': [device_id],
        'userFrom': user.email,
        'userTo': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirm': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    assert trade.devices[0].owner.email == user.email

    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [device_id]
    }

    user2.post(res=models.Action, data=request_confirm)
    user2.post(res=models.Action, data=request_confirm, status=422)
    assert len(trade.acceptances) == 2
    assert trade.devices[0].owner.email == user2.email


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_confirm_revoke(user: UserClient, user2: UserClient):
    """Check the normal revoke of one confirmation"""
    snapshot, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    device_id = snapshot['device']['id']
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    user.post({},
              res=Lot,
              item='{}/devices'.format(lot['id']),
              query=[('id', device_id)])

    request_post = {
        'type': 'Trade',
        'devices': [device_id],
        'userFrom': user.email,
        'userTo': user2.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirm': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [device_id]
    }

    request_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device_id],
    }


    # Normal confirmation
    user2.post(res=models.Action, data=request_confirm)

    # Normal revoke
    user2.post(res=models.Action, data=request_revoke)

    # Error for try duplicate revoke
    user2.post(res=models.Action, data=request_revoke, status=422)
    assert len(trade.acceptances) == 3

    # You can not to do one confirmation next of one revoke
    user2.post(res=models.Action, data=request_confirm, status=422)
    assert len(trade.acceptances) == 3


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_usecase_confirmation(user: UserClient, user2: UserClient):
    """Example of one usecase about confirmation"""
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)
    snap3, _ = user.post(file('asus-1001pxd.snapshot'), res=models.Snapshot)
    snap4, _ = user.post(file('desktop-9644w8n-lenovo-0169622.snapshot'), res=models.Snapshot)
    snap5, _ = user.post(file('laptop-hp_255_g3_notebook-hewlett-packard-cnd52270fw.snapshot'), res=models.Snapshot)
    snap6, _ = user.post(file('1-device-with-components.snapshot'), res=models.Snapshot)
    snap7, _ = user.post(file('asus-eee-1000h.snapshot.11'), res=models.Snapshot)
    snap8, _ = user.post(file('complete.export.snapshot'), res=models.Snapshot)
    snap9, _ = user.post(file('real-hp-quad-core.snapshot.11'), res=models.Snapshot)
    snap10, _ = user.post(file('david.lshw.snapshot'), res=models.Snapshot)

    devices = [('id', snap1['device']['id']),
               ('id', snap2['device']['id']),
               ('id', snap3['device']['id']),
               ('id', snap4['device']['id']),
               ('id', snap5['device']['id']),
               ('id', snap6['device']['id']),
               ('id', snap7['device']['id']),
               ('id', snap8['device']['id']),
               ('id', snap9['device']['id']),
               ('id', snap10['device']['id']),
              ]
    lot, _ = user.post({},
                       res=Lot,
                       item='{}/devices'.format(lot['id']),
                       query=devices[:7])

    # the manager shares the temporary lot with the SCRAP as an incoming lot 
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFrom': user2.email,
        'userTo': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirm': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    # the SCRAP confirms 3 of the 10 devices in its outgoing lot
    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [snap1['device']['id'], snap2['device']['id'], snap3['device']['id']]
    }
    assert trade.devices[0].actions[-2].t == 'Trade'
    assert trade.devices[0].actions[-1].t == 'Confirm'
    assert trade.devices[0].actions[-1].user == trade.user_to

    user2.post(res=models.Action, data=request_confirm)
    assert trade.devices[0].actions[-1].t == 'Confirm'
    assert trade.devices[0].actions[-1].user == trade.user_from
    n_actions = len(trade.devices[0].actions)

    # check validation error
    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [
            snap10['device']['id']
        ]
    }

    user2.post(res=models.Action, data=request_confirm, status=422)


    # The manager add 3 device more into the lot
    lot, _ = user.post({},
                       res=Lot,
                       item='{}/devices'.format(lot['id']),
                       query=devices[7:])

    assert trade.devices[-1].actions[-2].t == 'Trade'
    assert trade.devices[-1].actions[-1].t == 'Confirm'
    assert trade.devices[-1].actions[-1].user == trade.user_to
    assert len(trade.devices[0].actions) == n_actions


    # the SCRAP confirms the rest of devices
    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [
            snap1['device']['id'], 
            snap2['device']['id'], 
            snap3['device']['id'],
            snap4['device']['id'],
            snap5['device']['id'],
            snap6['device']['id'],
            snap7['device']['id'],
            snap8['device']['id'],
            snap9['device']['id'],
            snap10['device']['id']
        ]
    }

    user2.post(res=models.Action, data=request_confirm)
    assert trade.devices[-1].actions[-3].t == 'Trade'
    assert trade.devices[-1].actions[-1].t == 'Confirm'
    assert trade.devices[-1].actions[-1].user == trade.user_from
    assert len(trade.devices[0].actions) == n_actions

    # The manager remove one device of the lot and automaticaly 
    # is create one revoke action
    device_10 = trade.devices[-1]
    lot, _ = user.delete({},
                       res=Lot,
                       item='{}/devices'.format(lot['id']),
                       query=devices[-1:], status=200)
    assert len(trade.lot.devices) == len(trade.devices) == 9
    assert not device_10 in trade.devices
    assert device_10.actions[-1].t == 'Revoke'

    lot, _ = user.delete({},
                         res=Lot,
                         item='{}/devices'.format(lot['id']),
                         query=devices[-1:], status=200)

    assert device_10.actions[-1].t == 'Revoke'
    assert device_10.actions[-2].t == 'Confirm'

    # the SCRAP confirms the revoke action
    request_confirm_revoke = {
        'type': 'ConfirmRevoke',
        'action': device_10.actions[-1].id,
        'devices': [
            snap10['device']['id']
        ]
    }

    user2.post(res=models.Action, data=request_confirm_revoke)
    assert device_10.actions[-1].t == 'ConfirmRevoke'
    assert device_10.actions[-2].t == 'Revoke'

    request_confirm_revoke = {
        'type': 'ConfirmRevoke',
        'action': device_10.actions[-1].id,
        'devices': [
            snap9['device']['id']
        ]
    }

    # check validation error
    user2.post(res=models.Action, data=request_confirm_revoke, status=422)


    # The manager add again device_10
    assert len(trade.devices) == 9
    lot, _ = user.post({},
                       res=Lot,
                       item='{}/devices'.format(lot['id']),
                       query=devices[-1:])

    assert device_10.actions[-1].t == 'Confirm'
    assert device_10 in trade.devices
    assert len(trade.devices) == 10


    # the SCRAP confirms the action trade for device_10
    request_reconfirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [
            snap10['device']['id']
        ]
    }
    # import pdb; pdb.set_trace()
    user2.post(res=models.Action, data=request_reconfirm)
    assert device_10.actions[-1].t == 'Confirm'
    assert device_10.actions[-1].user == trade.user_from
    assert device_10.actions[-2].t == 'Confirm'
    assert device_10.actions[-2].user == trade.user_to
    assert device_10.actions[-3].t == 'ConfirmRevoke'
    assert len(device_10.actions) == 13


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_confirmRevoke(user: UserClient, user2: UserClient):
    """Example of one usecase about confirmation"""
    # the pRp (manatest_usecase_confirmationger) creates a temporary lot
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    # The manager add 7 device into the lot
    snap1, _ = user.post(file('basic.snapshot'), res=models.Snapshot)
    snap2, _ = user.post(file('acer.happy.battery.snapshot'), res=models.Snapshot)
    snap3, _ = user.post(file('asus-1001pxd.snapshot'), res=models.Snapshot)
    snap4, _ = user.post(file('desktop-9644w8n-lenovo-0169622.snapshot'), res=models.Snapshot)
    snap5, _ = user.post(file('laptop-hp_255_g3_notebook-hewlett-packard-cnd52270fw.snapshot'), res=models.Snapshot)
    snap6, _ = user.post(file('1-device-with-components.snapshot'), res=models.Snapshot)
    snap7, _ = user.post(file('asus-eee-1000h.snapshot.11'), res=models.Snapshot)
    snap8, _ = user.post(file('complete.export.snapshot'), res=models.Snapshot)
    snap9, _ = user.post(file('real-hp-quad-core.snapshot.11'), res=models.Snapshot)
    snap10, _ = user.post(file('david.lshw.snapshot'), res=models.Snapshot)

    devices = [('id', snap1['device']['id']),
               ('id', snap2['device']['id']),
               ('id', snap3['device']['id']),
               ('id', snap4['device']['id']),
               ('id', snap5['device']['id']),
               ('id', snap6['device']['id']),
               ('id', snap7['device']['id']),
               ('id', snap8['device']['id']),
               ('id', snap9['device']['id']),
               ('id', snap10['device']['id']),
              ]
    lot, _ = user.post({},
                       res=Lot,
                       item='{}/devices'.format(lot['id']),
                       query=devices)

    # the manager shares the temporary lot with the SCRAP as an incoming lot 
    # for the CRAP to confirm it
    request_post = {
        'type': 'Trade',
        'devices': [],
        'userFrom': user2.email,
        'userTo': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirm': True,
    }

    user.post(res=models.Action, data=request_post)
    trade = models.Trade.query.one()

    # the SCRAP confirms all of devices
    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [
            snap1['device']['id'], 
            snap2['device']['id'], 
            snap3['device']['id'],
            snap4['device']['id'],
            snap5['device']['id'],
            snap6['device']['id'],
            snap7['device']['id'],
            snap8['device']['id'],
            snap9['device']['id'],
            snap10['device']['id']
        ]
    }

    user2.post(res=models.Action, data=request_confirm)
    assert trade.devices[-1].actions[-3].t == 'Trade'
    assert trade.devices[-1].actions[-1].t == 'Confirm'
    assert trade.devices[-1].actions[-1].user == trade.user_from

    # The manager remove one device of the lot and automaticaly 
    # is create one revoke action
    device_10 = trade.devices[-1]
    lot, _ = user.delete({},
                       res=Lot,
                       item='{}/devices'.format(lot['id']),
                       query=devices[-1:], status=200)
    assert len(trade.lot.devices) == len(trade.devices) == 9
    assert not device_10 in trade.devices
    assert device_10.actions[-1].t == 'Revoke'

    lot, _ = user.delete({},
                         res=Lot,
                         item='{}/devices'.format(lot['id']),
                         query=devices[-1:], status=200)

    assert device_10.actions[-1].t == 'Revoke'
    assert device_10.actions[-2].t == 'Confirm'

    # The manager add again device_10
    assert len(trade.devices) == 9
    lot, _ = user.post({},
                       res=Lot,
                       item='{}/devices'.format(lot['id']),
                       query=devices[-1:])

    assert device_10.actions[-1].t == 'Confirm'
    assert device_10 in trade.devices
    assert len(trade.devices) == 10

    # the SCRAP confirms the revoke action
    request_confirm_revoke = {
        'type': 'ConfirmRevoke',
        'action': device_10.actions[-2].id,
        'devices': [
            snap10['device']['id']
        ]
    }

    # check validation error
    user2.post(res=models.Action, data=request_confirm_revoke, status=422)

    # the SCRAP confirms the action trade for device_10
    request_reconfirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [
            snap10['device']['id']
        ]
    }
    user2.post(res=models.Action, data=request_reconfirm)
    assert device_10.actions[-1].t == 'Confirm'
    assert device_10.actions[-1].user == trade.user_from
    assert device_10.actions[-2].t == 'Confirm'
    assert device_10.actions[-2].user == trade.user_to
    assert device_10.actions[-3].t == 'Revoke'


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_simple_add_document(user: UserClient):
    """Example of one document inserted into one lot"""
    doc = TradeDocument(**{'file_name': 'test', 'owner_id': user.user['id']})
    db.session.add(doc)
    db.session.flush()


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_add_document_to_lot(user: UserClient, user2: UserClient, client: Client, app: Devicehub):
    """Example of one document inserted into one lot"""
    lot, _ = user.post({'name': 'MyLot'}, res=Lot)
    data = {'lot': lot['id'], 'file_name': 'test.csv'}
    base64_bytes = base64.b64encode(b'This is a test')
    base64_string = base64_bytes.decode('utf-8')
    data['file'] = base64_string
    doc, _ = user.post(res=TradeDocument,
                       data=data)

    assert len(ReportHash.query.all()) == 1

    path_dir_base = os.path.join(app.config['PATH_DOCUMENTS_STORAGE'] , user.email)
    path = os.path.join(path_dir_base, lot['id'])
    assert len(os.listdir(path)) == 1
    # import pdb; pdb.set_trace()

    user.get(res=TradeDocument, item=doc['id'])
    user.delete(res=TradeDocument, item=doc['id'])

    # check permitions
    doc, _ = user.post(res=TradeDocument, data=data)

    # anonyms users
    client.get(res=TradeDocument, item=doc['id'], status=401)
    client.delete(res=TradeDocument, item=doc['id'], status=401)

    # other user
    user2.get(res=TradeDocument, item=doc['id'], status=404)
    user2.delete(res=TradeDocument, item=doc['id'], status=404)
    shutil.rmtree(path)
