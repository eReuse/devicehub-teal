import json

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.models import User


def register_user(email, password, rols="Operator"):
    # rols = 'Issuer, Operator, Witness, Verifier'
    user = User.query.filter_by(email=email).one()

    token_dlt = user.set_new_dlt_keys(password)
    result = user.allow_permitions(api_token=token_dlt, rols=rols)
    rols = user.get_rols(token_dlt=token_dlt)
    rols = [k for k, v in rols]
    user.rols_dlt = json.dumps(rols)

    db.session.commit()

    return result, rols
