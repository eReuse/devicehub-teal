from ereuse_devicehub.resources.device import models as m
from ereuse_devicehub.db import db

def migrate(app):
    with app.app_context():
        for c in m.Component.query.filter():
            if c.parent_id:
                c.owner_id = c.parent.owner.id
            db.session.add(c)
        db.session.commit()
        db.session.flush()
