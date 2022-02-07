import os
import ipaddress
import json
import shutil
import copy
import pytest
from datetime import datetime
from dateutil.tz import tzutc
from ereuse_devicehub.client import UserClient
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.deliverynote.models import Deliverynote
from tests import conftest


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_simple_deliverynote(user: UserClient, app: Devicehub):
    """
    This test create only one deliverinote with the expected Devices
    """
    inventory = [{'n_inventory': 'N006536',
                  'type': 'PC',
                  'brand': 'Acer',
                  'model': 'Veriton M480G',
                  'serial_number': 'PSV75EZ0070170002C14j00'
    }]
    note = {'date': datetime(2020, 2, 14, 23, 0, tzinfo=tzutc()),
            'documentID': 'DocBBE001',
            'amount': 0,
            'transfer_state': "Initial",
            'expectedDevices': inventory,
            'supplierEmail': user.user['email']}

    deliverynote, _ = user.post(note, res=Deliverynote)
    db_note = Deliverynote.query.filter_by(id=deliverynote['id']).one()

    assert deliverynote['documentID'] == note['documentID']
    assert deliverynote['documentID'] in db_note.lot.name
