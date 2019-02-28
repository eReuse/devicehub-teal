from boltons.typeutils import classproperty
from flask import current_app

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.models import Thing


class Inventory(Thing):
    id = db.Column(db.Unicode(), primary_key=True)
    id.comment = """The name of the inventory as in the URL and schema."""
    name = db.Column(db.CIText(), nullable=False, unique=True)
    name.comment = """The human name of the inventory."""
    tag_provider = db.Column(db.URL(), nullable=False)
    tag_token = db.Column(db.UUID(as_uuid=True), unique=True, nullable=False)
    tag_token.comment = """The token to access a Tag service."""
    # todo no validation that UUID is from an existing organization
    org_id = db.Column(db.UUID(as_uuid=True), nullable=False)

    __table_args__ = (
        db.Index('id_hash', id, postgresql_using='hash'),
        {'schema': 'common'}
    )

    @classproperty
    def current(cls) -> 'Inventory':
        """The inventory of the current_app."""
        return Inventory.query.filter_by(id=current_app.id).one()
