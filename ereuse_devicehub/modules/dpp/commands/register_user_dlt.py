import json

import click

from flask import current_app as app
from ereuseapi.methods import register_user
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.modules.dpp.utils import encrypt


class RegisterUserDlt:
    #  "Operator", "Verifier" or "Witness"

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        help = "Insert users than are in Dlt with params: path of data set file"
        self.app.cli.command('dlt_register_user', short_help=help)(self.run)

    @click.argument('dataset_file')
    def run(self, dataset_file):
        with open(dataset_file) as f:
            dataset = json.loads(f.read())

        for d in dataset:
            self.add_user(d)

        db.session.commit()

    def add_user(self, data):
        email = data.get("email")
        name = email.split('@')[0]
        password = data.get("password")
        eth_priv_key = data.get("eth_priv_key")
        eth_pub_key = data.get("eth_pub_key")
        user = User.query.filter_by(email=email).first()
        import pdb; pdb.set_trace()

        if not user:
            user = User(email=email, password=password)
            user.individuals.add(Person(name=name))

        api_dlt = app.config.get('API_DLT')
        try:
            response = register_user(api_dlt, eth_priv_key)
            api_token = response.get('data', {}).get('api_token')
        except Exception:
            api_token = ""
        ethereum = {
            "eth_pub_key": eth_pub_key,
            "eth_priv_key": eth_priv_key,
            "api_token": api_token
        }
        data_eth = json.dumps(ethereum)
        user.api_keys_dlt = encrypt(password, data_eth)

        try:
            attributes = user.get_abac_attributes()
            roles = attributes.get("role", ["Operator"])
        except Exception:
            roles ["Operator"]

        user.rols_dlt = json.dumps(roles)

        if not user.id:
            db.session.add(user)
