import datetime
from uuid import UUID
from flask import g

import pytest
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

"""
Action.main                        POST                     /actions/
Action.main                        DELETE, GET, PATCH, PUT  /actions/<uuid:id>
Action.main                        GET                      /actions/
Deliverynote.main                  POST                     /deliverynotes/
Deliverynote.main                  DELETE, GET, PATCH, PUT  /deliverynotes/<uuid:id>
Deliverynote.main                  GET                      /deliverynotes/
Device.main                        POST                     /devices/
Device.main                        DELETE, GET, PATCH, PUT  /devices/<int:id>
Device.main                        GET                      /devices/
Device.static                      GET                      /devices/static/<path:filename>
Document.devicesDocumentView       GET                      /documents/devices/
Document.main                      GET                      /documents/erasures/<string:id>
Document.main                      GET                      /documents/erasures/
Document.static                    GET                      /documents/static/<path:filename>
Lot.lot-children                   DELETE, POST             /lots/<uuid:id>/children
Lot.lot-device                     DELETE, POST             /lots/<uuid:id>/devices
Lot.main                           POST                     /lots/
Lot.main                           DELETE, GET, PATCH, PUT  /lots/<uuid:id>
Lot.main                           GET                      /lots/
Manufacturer.main                  POST                     /manufacturers/
Manufacturer.main                  DELETE, GET, PATCH, PUT  /manufacturers/<string:id>
Manufacturer.main                  GET                      /manufacturers/
Proof.main                         POST                     /proofs/
Proof.main                         DELETE, GET, PATCH, PUT  /proofs/<uuid:id>
Proof.main                         GET                      /proofs/
Tag.main                           POST                     /tags/
Tag.main                           DELETE, GET, PATCH, PUT  /tags/<lower:id>
Tag.main                           GET                      /tags/
Tag.tag-device-view                PUT                      /tags/<lower:tag_id>/device/<int:device_id>
Tag.tag-device-view                GET                      /tags/<lower:id>/device
User.main                          POST                     /users/
User.main                          DELETE, GET, PATCH, PUT  /users/<uuid:id>
User.main                          GET                      /users/
"""


@pytest.mark.mvp_one
def test_users(user: UserClient, client: Client):
    """
    User.main POST /users/
    User.main DELETE, GET, PATCH, PUT /users/<uuid:id>
    User.main GET /users/
    """
    url = "/users/"
    ## User validated
    # GET
    import pdb; pdb.set_trace()
    content, res = user.get(url, None)
    assert res.status_code == 200
    content, res = client.get(url, None)
    assert res.status_code == 405

    # POST
    content, res = user.post(url, None)
    assert res.status_code == 200
    content, res = client.post(url, None)
    assert res.status_code == 405


    ##
    url = "/users/"+user.user["id"]
    # GET
    content, res = user.get(url, None)
    assert res.status_code == 200
    content, res = client.get(url, None)
    assert res.status_code == 405

    # DELETE
    content, res = user.delete(url, None)
    assert res.status_code == 200
    content, res = client.delete(url, None)
    assert res.status_code == 405

    # PUT
    content, res = user.put(url, None)
    assert res.status_code == 200
    content, res = client.put(url, None)
    assert res.status_code == 405

    # PATCH
    content, res = user.patch(url, None)
    assert res.status_code == 200
    content, res = client.patch(url, None)
    assert res.status_code == 405




@pytest.mark.mvp
def test_get_static(client: Client):
    """ static GET /static/<path:filename> """
    content, res = client.get("/static/file1.jpg", None)
    assert res.status_code == 200


@pytest.mark.mvp_one
def test_get_device(app: Devicehub, user: UserClient, client: Client):
    """Checks GETting a d.Desktop with its components."""

    with app.app_context():
        pc = d.Desktop(model='p1mo',
                       manufacturer='p1ma',
                       serial_number='p1s',
                       chassis=ComputerChassis.Tower,
                       owner_id=user.user['id'])
        db.session.add(pc)
        db.session.add(TestConnectivity(device=pc,
                                        severity=Severity.Info,
                                        agent=Person(name='Timmy'),
                                        author=User(email='bar@bar.com')))
        db.session.commit()

    pc, res = user.get("/devices/1/", None)
    assert res.status_code == 200

    pc = pc['items'][0]
    assert len(pc['actions']) == 1
    assert pc['actions'][0]['type'] == 'TestConnectivity'
    assert pc['actions'][0]['device'] == 1
    assert pc['actions'][0]['severity'] == 'Info'
    assert UUID(pc['actions'][0]['author'])
    assert 'actions_components' not in pc, 'actions_components are internal use only'
    assert 'actions_one' not in pc, 'they are internal use only'
    assert 'author' not in pc
    assert pc['hid'] == 'desktop-p1ma-p1mo-p1s'
    assert pc['model'] == 'p1mo'
    assert pc['manufacturer'] == 'p1ma'
    assert pc['serialNumber'] == 'p1s'
    assert pc['type'] == d.Desktop.t


@pytest.mark.mvp
def test_get_devices(app: Devicehub, user: UserClient, client: Client):
    """Checks GETting multiple devices."""

    with app.app_context():
        pc = d.Desktop(model='p1mo',
                       manufacturer='p1ma',
                       serial_number='p1s',
                       chassis=ComputerChassis.Tower,
                       owner_id=user.user['id'])
        pc.components = OrderedSet([
            d.NetworkAdapter(model='c1mo', manufacturer='c1ma', serial_number='c1s'),
            d.GraphicCard(model='c2mo', manufacturer='c2ma', memory=1500)
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

    devices, res = client.get("/devices/", None)
    assert len(devices) == 3
    assert res.status_code == 200
