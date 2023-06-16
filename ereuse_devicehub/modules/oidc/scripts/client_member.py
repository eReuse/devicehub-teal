import sys

from decouple import config

from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.modules.oidc.models import MemberFederated


def main():
    """
    We need add client_id and client_secret for every server
    than we want connect.
    """
    schema = config('DB_SCHEMA')
    app = Devicehub(inventory=schema)
    app.app_context().push()
    domain = sys.argv[1]
    client_id = sys.argv[2]
    client_secret = sys.argv[3]
    member = MemberFederated.query.filter_by(domain=domain).first()
    if not member:
        return

    member.client_id = client_id
    member.client_secret = client_secret

    db.session.commit()


if __name__ == '__main__':
    main()
