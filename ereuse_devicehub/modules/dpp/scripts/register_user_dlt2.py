import json
import sys

from decouple import config
from ereuseapi.methods import API, register_user

from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.modules.dpp.utils import encrypt
from ereuse_devicehub.resources.user.models import User


def main():
    email = sys.argv[1]
    password = sys.argv[2]
    schema = config('DB_SCHEMA')
    app = Devicehub(inventory=schema)
    app.app_context().push()
    api_dlt = app.config.get('API_DLT')
    keyUser1 = app.config.get('API_DLT_TOKEN')

    user = User.query.filter_by(email=email).one()

    data = register_user(api_dlt)
    api_token = data.get('data', {}).get('api_token')
    data = json.dumps(data)
    user.api_keys_dlt = encrypt(password, data)
    result = allow_permitions(keyUser1, api_dlt, api_token)
    rols = get_rols(api_dlt, api_token)
    user.rols_dlt = json.dumps(rols)

    db.session.commit()

    return result, rols


def get_rols(api_dlt, token_dlt):
    api = API(api_dlt, token_dlt, "ethereum")

    result = api.check_user_roles()
    if result.get('Status') != 200:
        return []

    if 'Success' not in result.get('Data', {}).get('status'):
        return []

    rols = result.get('Data', {}).get('data', {})
    return [k for k, v in rols.items() if v]


def allow_permitions(keyUser1, api_dlt, token_dlt):
    apiUser1 = API(api_dlt, keyUser1, "ethereum")
    rols = "isOperator"
    if len(sys.argv) > 3:
        rols = sys.argv[3]

    result = apiUser1.issue_credential(rols, token_dlt)
    return result


if __name__ == '__main__':
    # ['isIssuer', 'isOperator', 'isWitness', 'isVerifier']
    main()
