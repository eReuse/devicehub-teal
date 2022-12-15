from flask import current_app as app
from marshmallow import Schema as MarshmallowSchema
from marshmallow import ValidationError, validates_schema
from marshmallow.fields import Dict, List, Nested, String

from ereuse_devicehub.resources.schemas import Thing


class Snapshot_lite_data(MarshmallowSchema):
    dmidecode = String(required=True)
    hwinfo = String(required=True)
    smart = List(Dict(), required=True)
    lshw = Dict(required=True)
    lspci = String(required=True)


class Snapshot_lite(Thing):
    uuid = String(required=True)
    version = String(required=True)
    schema_api = String(required=True)
    software = String(required=True)
    sid = String(required=True)
    type = String(required=True)
    timestamp = String(required=True)
    settings_version = String(required=False)
    data = Nested(Snapshot_lite_data, required=True)

    @validates_schema
    def validate_workbench_version(self, data: dict):
        if data['schema_api'] not in app.config['SCHEMA_WORKBENCH']:
            raise ValidationError(
                'Min. supported Workbench version is '
                '{} but yours is {}.'.format(
                    app.config['SCHEMA_WORKBENCH'][0], data['version']
                ),
                field_names=['version'],
            )
