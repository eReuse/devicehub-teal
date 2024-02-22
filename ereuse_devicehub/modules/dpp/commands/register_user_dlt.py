import json
import requests

import click

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

        for d in dataset:
            self.add_user(d)

            db.session.commit()

    def add_user(self, data):
        email = data.get("email")
        name = email.split('@')[0]
        password = data.get("password")
        api_dlt = app.config.get('API_DLT')
        eth_priv_key = data.get("eth_priv_key")
        eth_pub_key = data.get("eth_pub_key")

        user = User.query.filter_by(email=email).first()

        if not user:
            user = User(email=email, password=password)
            user.individuals.add(Person(name=name))

        try:
            response = register_user(api_dlt, privateKey=eth_priv_key[2:])
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

        roles = []
        try:
            abac_tk = app.config.get('ABAC_TOKEN')
            domain = app.config.get('ABAC_URL')
            eth_pub_key = eth_pub_key

            header = {
                'Authorization': f'Bearer {abac_tk}',
            }
            url = f'{domain}{eth_pub_key}/attributes'
            r = requests.get(url, headers=header)
            attributes = {}
            for j in r.json():
                k = j.get('attributeURI', '').split('/')[-1].split("#")[-1]
                v = j.get('attributeValue', '').strip()
                if not (k and v):
                    continue
                attributes[k] = v

            if attributes.get('role'):
                roles.append(attributes.get('role'))
        except Exception:
            roles = ["operator"]

        user.rols_dlt = json.dumps(roles)

        db.session.add(user)
