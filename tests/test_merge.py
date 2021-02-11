import datetime
from uuid import UUID
from flask import g

import pytest
from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.action import models as m
from ereuse_devicehub.resources.device import models as d
from ereuse_devicehub.resources.tag import Tag
from tests import conftest
from tests.conftest import file as import_snap


@pytest.mark.mvp
def test_deactivate_merge(app: Devicehub, user: UserClient):
    """ Check if is correct to do a manual merge """
    snapshot1, _ = user.post(import_snap('real-custom.snapshot.11'), res=m.Snapshot)
    snapshot2, _ = user.post(import_snap('real-hp.snapshot.11'), res=m.Snapshot)
    pc1_id = snapshot1['device']['id']
    pc2_id = snapshot2['device']['id']

    with app.app_context():
        pc1 = d.Device.query.filter_by(id=pc1_id).one()
        pc2 = d.Device.query.filter_by(id=pc2_id).one()
        n_actions1 = len(pc1.actions)
        n_actions2 = len(pc2.actions)
        action1 = pc1.actions[0]
        action2 = pc2.actions[0]
        assert not action2 in pc1.actions

        tag = Tag(id='foo-bar', owner_id=user.user['id'])
        pc2.tags.add(tag)
        db.session.add(pc2)
        db.session.commit()

        components1 = [com for com in pc1.components]
        components2 = [com for com in pc2.components]
        components1_excluded = [com for com in pc1.components if not com in components2]
        assert pc1.hid != pc2.hid
        assert not tag in pc1.tags

        uri = '/devices/%d/merge/%d' % (pc1_id, pc2_id)
        _, code = user.post({'id': 1}, uri=uri, status=404)
        assert code.status == '404 NOT FOUND'

# @pytest.mark.mvp
def test_simple_merge(app: Devicehub, user: UserClient):
    """ Check if is correct to do a manual merge """
    snapshot1, _ = user.post(import_snap('real-custom.snapshot.11'), res=m.Snapshot)
    snapshot2, _ = user.post(import_snap('real-hp.snapshot.11'), res=m.Snapshot)
    pc1_id = snapshot1['device']['id']
    pc2_id = snapshot2['device']['id']

    with app.app_context():
        pc1 = d.Device.query.filter_by(id=pc1_id).one()
        pc2 = d.Device.query.filter_by(id=pc2_id).one()
        n_actions1 = len(pc1.actions)
        n_actions2 = len(pc2.actions)
        action1 = pc1.actions[0]
        action2 = pc2.actions[0]
        assert not action2 in pc1.actions

        tag = Tag(id='foo-bar', owner_id=user.user['id'])
        pc2.tags.add(tag)
        db.session.add(pc2)
        db.session.commit()

        components1 = [com for com in pc1.components]
        components2 = [com for com in pc2.components]
        components1_excluded = [com for com in pc1.components if not com in components2]
        assert pc1.hid != pc2.hid
        assert not tag in pc1.tags

        uri = '/devices/%d/merge/%d' % (pc1_id, pc2_id)
        result, _ = user.post({'id': 1}, uri=uri, status=201)

        assert pc1.hid == pc2.hid
        assert action1 in pc1.actions
        assert action2 in pc1.actions
        assert len(pc1.actions) == n_actions1 + n_actions2
        assert set(pc2.components) == set()
        assert tag in pc1.tags
        assert not tag in pc2.tags

        for com in components2:
            assert com in pc1.components

        for com in components1_excluded:
            assert not com in pc1.components

# @pytest.mark.mvp
def test_merge_two_device_with_differents_tags(app: Devicehub, user: UserClient):
    """ Check if is correct to do a manual merge of 2 diferents devices with diferents tags """
    snapshot1, _ = user.post(import_snap('real-custom.snapshot.11'), res=m.Snapshot)
    snapshot2, _ = user.post(import_snap('real-hp.snapshot.11'), res=m.Snapshot)
    pc1_id = snapshot1['device']['id']
    pc2_id = snapshot2['device']['id']

    with app.app_context():
        pc1 = d.Device.query.filter_by(id=pc1_id).one()
        pc2 = d.Device.query.filter_by(id=pc2_id).one()

        tag1 = Tag(id='fii-bor', owner_id=user.user['id'])
        tag2 = Tag(id='foo-bar', owner_id=user.user['id'])
        pc1.tags.add(tag1)
        pc2.tags.add(tag2)
        db.session.add(pc1)
        db.session.add(pc2)
        db.session.commit()

        uri = '/devices/%d/merge/%d' % (pc1_id, pc2_id)
        result, _ = user.post({'id': 1}, uri=uri, status=201)

        assert pc1.hid == pc2.hid
        assert tag1 in pc1.tags
        assert tag2 in pc1.tags

