import datetime
from uuid import UUID
from flask import g

import pytest
from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.action import models as m
from ereuse_devicehub.resources.device import models as d
from tests import conftest
from tests.conftest import file as import_snap


@pytest.mark.mvp
def test_simple_merge(app: Devicehub, user: UserClient):
    snapshot1, _ = user.post(import_snap('basic.snapshot'), res=m.Snapshot)
    snapshot2, _ = user.post(import_snap('real-eee-1001pxd.snapshot.12'), res=m.Snapshot)
    pc1_id = snapshot1['device']['id']
    pc2_id = snapshot2['device']['id']

    # import pdb; pdb.set_trace()
    with app.app_context():
        pc1_1 = d.Device.query.filter_by(id=snapshot1['device']['id']).one()
        pc2_1 = d.Device.query.filter_by(id=snapshot2['device']['id']).one()
        
        result, _ = user.post({'id': 1}, uri='/devices/%d/merge/%d' % (pc1_id, pc2_id), status=201)

        pc1_2 = d.Device.query.filter_by(id=snapshot1['device']['id']).one()
        pc2_2 = d.Device.query.filter_by(id=snapshot2['device']['id']).one()


