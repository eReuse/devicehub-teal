import datetime
import pkg_resources
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


@pytest.mark.mvp
@pytest.mark.xfail(reason='We need think about specifications.')
def test_users(user: UserClient, client: Client):
    """
    User.main POST /users/
    User.main DELETE, GET, PATCH, PUT /users/<uuid:id>
    User.main GET /users/
    """
    url = "/users/"
    ## User validated
    # GET
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
def test_get_version(app: Devicehub, client: Client):
    """Checks GETting versions of services."""

    content, res = client.get("/versions/", None)
    with open("ereuse_devicehub/__init__.py", encoding="utf8") as f:
            dh_version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)
    version = {'devicehub': dh_version, 'ereuse_tag': '0.0.0'}
    assert res.status_code == 200
    assert content == version

@pytest.mark.mvp
def test_get_device(app: Devicehub, user: UserClient, user2: UserClient):
    """Checks GETting a d.Desktop with its components."""

    user.post(file('asus-eee-1000h.snapshot.11'), res=m.Snapshot)
    pc, res = user.get("/devices/1", None)
    assert res.status_code == 200
    assert len(pc['actions']) == 9

    pc2, res2 = user2.get("/devices/1", None)
    assert res2.status_code == 200
    assert pc2 == {}


@pytest.mark.mvp
def test_get_devices(app: Devicehub, user: UserClient, user2: UserClient):
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
def test_get_tag(app: Devicehub, user: UserClient, user2: UserClient):
    """Creates a tag specifying a custom organization."""
    with app.app_context():
        # Create a pc with a tag
        tag = Tag(id='foo-bar', owner_id=user.user['id'])
        pc = d.Desktop(serial_number='sn1', chassis=ComputerChassis.Tower, owner_id=user.user['id'])
        pc.tags.add(tag)
        db.session.add(pc)
        db.session.commit()
    computer, res = user.get(res=Tag, item='foo-bar/device')

    url = "/tags/?foo-bar/device"
    computer, res = user.get(url, None)
    computer2, res2 = user2.get(url, None)
    assert res.status_code == 200
    assert res2.status_code == 200
    assert len(computer['items']) == 1
    assert len(computer2['items']) == 0
