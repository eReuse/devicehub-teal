from base64 import b64encode

from marshmallow import pre_dump
from marshmallow.fields import Email, String, UUID

from ereuse_devicehub.resources.schemas import Thing


class User(Thing):
    id = UUID(dump_only=True)
    email = Email(required=True)
    password = String(load_only=True, required=True)
    token = String(dump_only=True,
                   description='Use this token in an Authorization header to access the app.'
                               'The token can change overtime.')

    @pre_dump
    def base64encode_token(self, data: dict):
        """Encodes the token to base64 so clients don't have to."""
        # framework needs ':' at the end
        data['token'] = b64encode(str.encode(str(data['token']) + ':'))
        return data
