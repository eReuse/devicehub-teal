import json
import requests

import click

from ereuseapi.methods import API
from flask import g, current_app as app
from ereuseapi.methods import register_user
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.modules.dpp.utils import encrypt


class RegisterUserDlt:
    #  "operator", "verifier" or "witness"

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        help = "Insert users than are in Dlt with params: path of data set file"
        self.app.cli.command('dlt_register_user', short_help=help)(self.run)

    @click.argument('dataset_file')
    def run(self, dataset_file):
        with open(dataset_file) as f:
            dataset = json.loads(f.read())

        self.add_user(dataset)

        db.session.commit()

    def add_user(self, data):
        email = data.get("email")
        name = email.split('@')[0]
        password = data.get("password")
        api_token = data.get("api_token")
        ethereum = {"data": {"api_token": api_token}}

        user = User.query.filter_by(email=email).first()

        if not user:
            user = User(email=email, password=password)
            user.individuals.add(Person(name=name))

        data_eth = json.dumps(ethereum)
        user.api_keys_dlt = encrypt(password, data_eth)

        roles = []
        token_dlt = api_token
        api_dlt = app.config.get('API_DLT')
        api = API(api_dlt, token_dlt, "ethereum")
        result = api.check_user_roles()

        if result.get('Status') == 200:
            if 'Success' in result.get('Data', {}).get('status'):
                rols = result.get('Data', {}).get('data', {})
                roles = [(k, k) for k, v in rols.items() if v]

        user.rols_dlt = json.dumps(roles)

        db.session.add(user)
