import sys

from decouple import config

from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.modules.oidc.models import MemberFederated


def main():
    schema = config('DB_SCHEMA')
    app = Devicehub(inventory=schema)
    app.app_context().push()
    dlt_id_provider = sys.argv[1]
    domain = sys.argv[2]
    member = MemberFederated.query.filter_by(domain=domain).first()
    if member:
        return

    member = MemberFederated(domain=domain, dlt_id_provider=dlt_id_provider)

    db.session.add(member)
    db.session.commit()


if __name__ == '__main__':
    main()
