from marshmallow.fields import DateTime, List, Str, URL, Nested
from teal.resource import Schema


class Thing(Schema):
    url = URL(dump_only=True, description='The URL of the resource.')
    same_as = List(URL(dump_only=True), dump_only=True)
    updated = DateTime('iso', dump_only=True)
    created = DateTime('iso', dump_only=True)
    author = Nested('User', only='id', dump_only=True)
