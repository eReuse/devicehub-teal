import ereuse_devicehub.teal.marshmallow
from marshmallow import fields as mf

from ereuse_devicehub.resources.schemas import Thing


class Inventory(Thing):
    id = mf.String(dump_only=True)
    name = mf.String(dump_only=True)
    tag_provider = ereuse_devicehub.teal.marshmallow.URL(
        dump_only=True, data_key='tagProvider'
    )
