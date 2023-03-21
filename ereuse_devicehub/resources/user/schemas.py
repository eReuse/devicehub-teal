from marshmallow import post_dump
from marshmallow.fields import UUID, Email, String

from ereuse_devicehub import auth
from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.agent.schemas import Individual
from ereuse_devicehub.resources.inventory.schema import Inventory
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.teal.marshmallow import SanitizedStr


class Session(Thing):
    token = String(dump_only=True)


class User(Thing):
    id = UUID(dump_only=True)
    email = Email(required=True)
    password = SanitizedStr(load_only=True, required=True)
    individuals = NestedOn(Individual, many=True, dump_only=True)
    name = SanitizedStr()
    token = String(
        dump_only=True,
        description='Use this token in an Authorization header to access the app.'
        'The token can change overtime.',
    )
    inventories = NestedOn(Inventory, many=True, dump_only=True)
    code = String(dump_only=True, description='Code of inactive accounts')

    def __init__(
        self,
        only=None,
        exclude=('token',),
        prefix='',
        many=False,
        context=None,
        load_only=(),
        dump_only=(),
        partial=False,
    ):
        """Instantiates the User.

        By default we exclude token from both load/dump
        so they are not taken / set in normal usage by mistake.
        """
        super().__init__(
            only, exclude, prefix, many, context, load_only, dump_only, partial
        )

    @post_dump
    def base64encode_token(self, data: dict):
        """Encodes the token to base64 so clients don't have to."""
        if 'token' in data:
            # In many cases we don't dump the token (ex. relationships)
            # Framework needs ':' at the end
            data['token'] = auth.Auth.encode(data['token'])
        return data
