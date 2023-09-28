import click
import requests
from decouple import config


class InsertMember:
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        help = 'Add a new members to api dlt.'
        self.app.cli.command('dlt_insert_members', short_help=help)(self.run)

    @click.argument('domain')
    def run(self, domain):
        api = config("API_RESOLVER", None)
        if "http" not in domain:
            print("Error: you need put https:// in domain")
            return

        if not api:
            print("Error: you need a entry var API_RESOLVER in .env")
            return

        api = api.strip("/")
        domain = domain.strip("/")

        data = {"url": domain}
        url = api + '/registerURL'
        res = requests.post(url, json=data)
        print(res.json())
        return
