from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.models import User


def set_dlt_user(email, password):
    u = User.query.filter_by(email=email).one()
    api_token = u.set_new_dlt_keys(password)
    u.allow_permitions(api_token)
    db.session.commit()
