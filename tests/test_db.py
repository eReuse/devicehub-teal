import datetime
from uuid import UUID

import pytest

from ereuse_devicehub.teal.db import UniqueViolation


@pytest.mark.mvp
def test_unique_violation():
    class IntegrityErrorMock:
        def __init__(self) -> None:
            self.params = {
                'uuid': UUID('f5efd26e-8754-46bc-87bf-fbccc39d60d9'),
                'version': '11.0',
                'software': 'Workbench',
                'elapsed': datetime.timedelta(0, 4),
                'expected_actions': None,
                'id': UUID('dbdef3d8-2cac-48cb-adb8-419bc3e59687'),
            }

        def __str__(self):
            return """(psycopg2.IntegrityError) duplicate key value violates unique constraint "snapshot_uuid_key"
            DETAIL:  Key (uuid)=(f5efd26e-8754-46bc-87bf-fbccc39d60d9) already exists.
            [SQL: 'INSERT INTO snapshot (uuid, version, software, elapsed, expected_actions, id) 
            VALUES (%(uuid)s, %(version)s, %(software)s, %(elapsed)s, CAST(%(expected_actions)s 
            AS snapshotexpectedactions[]), %(id)s)'] [parameters: {'uuid': UUID('f5efd26e-8754-46bc-87bf-fbccc39d60d9'), 
            'version': '11.0', 'software': 'Workbench', 'elapsed': datetime.timedelta(0, 4), 'expected_actions': None, 
            'id': UUID('dbdef3d8-2cac-48cb-adb8-419bc3e59687')}] (Background on this error at: http://sqlalche.me/e/gkpj)"""

    u = UniqueViolation(IntegrityErrorMock())
    assert u.constraint == 'snapshot_uuid_key'
    assert u.field_name == 'uuid'
    assert u.field_value == UUID('f5efd26e-8754-46bc-87bf-fbccc39d60d9')
