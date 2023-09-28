import requests
from decouple import config

from ereuse_devicehub.db import db
from ereuse_devicehub.modules.oidc.models import MemberFederated


class GetMembers:
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.app.cli.command(
            'dlt_rsync_members', short_help='Synchronize members of dlt.'
        )(self.run)

    def run(self):
        api = config("API_RESOLVER", None)
        if not api:
            print("Error: you need a entry var API_RESOLVER in .env")
            return

        api = api.strip("/")

        url = api + '/getAll'
        res = requests.get(url)
        if res.status_code != 200:
            return "Error, {}".format(res.text)
        response = res.json()
        members = response['url']
        counter = members.pop('counter')
        if counter <= MemberFederated.query.count():
            return "All ok"

        for k, v in members.items():
            id = self.clean_id(k)
            member = MemberFederated.query.filter_by(dlt_id_provider=id).first()
            if member:
                if member.domain != v:
                    member.domain = v
                continue
            member = MemberFederated(dlt_id_provider=id, domain=v)
            db.session.add(member)
        db.session.commit()
        return res.text

    def clean_id(self, id):
        return int(id.split('DH')[-1])
