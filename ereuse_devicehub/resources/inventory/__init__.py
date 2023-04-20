import uuid

import boltons.urlutils
from flask import current_app

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.inventory import schema
from ereuse_devicehub.resources.inventory.model import Inventory
from ereuse_devicehub.teal.db import ResourceNotFound
from ereuse_devicehub.teal.resource import Resource


class InventoryDef(Resource):
    SCHEMA = schema.Inventory
    VIEW = None

    def __init__(
        self,
        app,
        import_name=__name__.split('.')[0],
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
        )

    @classmethod
    def set_inventory_config(
        cls,
        name: str = None,
        org_name: str = None,
        org_id: str = None,
        tag_url: boltons.urlutils.URL = None,
        tag_token: uuid.UUID = None,
    ):
        try:
            inventory = Inventory.current
        except ResourceNotFound:  # No inventory defined in db yet
            inventory = Inventory(
                id=current_app.id, name=name, tag_provider=tag_url, tag_token=tag_token
            )
            db.session.add(inventory)
        if org_name or org_id:
            from ereuse_devicehub.resources.agent.models import Organization

            try:
                org = Organization.query.filter_by(tax_id=org_id, name=org_name).one()
            except ResourceNotFound:
                org = Organization(tax_id=org_id, name=org_name)
            org.default_of = inventory
        if tag_url:
            inventory.tag_provider = tag_url
        if tag_token:
            inventory.tag_token = tag_token

    @classmethod
    def delete_inventory(cls):
        """Removes an inventory alongside with the users that have
        only access to this inventory.
        """
        from ereuse_devicehub.resources.user.models import User, UserInventory

        inv = Inventory.query.filter_by(id=current_app.id).one()
        db.session.delete(inv)
        db.session.flush()
        # Remove users that end-up without any inventory
        # todo this should be done in a trigger / action
        users = User.query.filter(
            User.id.notin_(db.session.query(UserInventory.user_id).distinct())
        )
        for user in users:
            db.session.delete(user)
