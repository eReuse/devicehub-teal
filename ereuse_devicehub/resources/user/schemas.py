from base64 import b64encode

from marshmallow import post_dump
from marshmallow.fields import Email, String, UUID

from ereuse_devicehub.resources.schemas import Thing


class User(Thing):
    id = UUID(dump_only=True)
    email = Email(required=True)
    password = String(load_only=True, required=True)
    name = String()
    token = String(dump_only=True,
                   description='Use this token in an Authorization header to access the app.'
                               'The token can change overtime.')

    def __init__(self,
                 only=None,
                 exclude=('token',),
                 prefix='',
                 many=False,
                 context=None,
                 load_only=(),
                 dump_only=(),
                 partial=False):
        """
        Instantiates the User.

        By default we exclude token from both load/dump
        so they are not taken / set in normal usage by mistake.
        """
        super().__init__(only, exclude, prefix, many, context, load_only, dump_only, partial)

    @post_dump
    def base64encode_token(self, data: dict):
        """Encodes the token to base64 so clients don't have to."""
        if 'token' in data:
            # In many cases we don't dump the token (ex. relationships)
            # Framework needs ':' at the end
            data['token'] = b64encode(str.encode(str(data['token']) + ':')).decode()
        return data
