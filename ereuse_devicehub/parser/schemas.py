from flask import current_app as app
from marshmallow import Schema as MarshmallowSchema
from marshmallow import ValidationError, validates_schema
from marshmallow.fields import Dict, List, Nested, String

from ereuse_devicehub.resources.schemas import Thing


class Snapshot_lite_data(MarshmallowSchema):
    dmidecode = String(required=False)
    hwinfo = String(required=False)
    smart = List(Dict(), required=False)
    lshw = Dict(required=False)


class Snapshot_lite(Thing):
    uuid = String(required=True)
    version = String(required=True)
    schema_version = String(required=True)
    software = String(required=True)
    wbid = String(required=True)
    type = String(required=True)
    timestamp = String(required=True)
    data = Nested(Snapshot_lite_data)

    @validates_schema
    def validate_workbench_version(self, data: dict):
        if data['schema_version'] not in app.config['WORKBENCH_LITE']:
            raise ValidationError(
                'Min. supported Workbench version is '
                '{} but yours is {}.'.format(
                    app.config['WORKBENCH_LITE'][0], data['version']
                ),
                field_names=['version'],
            )
