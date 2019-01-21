from ereuse_devicehub.db import db
from ereuse_devicehub.resources.models import Thing


class Inventory(Thing):
    __table_args__ = {'schema': 'common'}
    id = db.Column(db.Unicode(), primary_key=True)
    id.comment = """The name of the inventory as in the URL and schema."""
    name = db.Column(db.CIText(), nullable=False, unique=True)
    name.comment = """The human name of the inventory."""
    tag_token = db.Column(db.UUID(as_uuid=True), unique=True)
    tag_token.comment = """The token to access a Tag service."""
