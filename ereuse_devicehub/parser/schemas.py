from flask import current_app as app
from marshmallow import Schema as MarshmallowSchema
from marshmallow import ValidationError, validates_schema
from marshmallow.fields import Dict, List, Nested, String

from ereuse_devicehub.resources.schemas import Thing

# from marshmallow_enum import EnumField


class Snapshot_lite_data(MarshmallowSchema):
    hwmd_version = String(required=True)
    lshw = Dict(required=True)
    dmidecode = String(required=True)
    lspci = String(required=True)
    hwinfo = String(required=True)
    smart = List(Dict(), required=False)


class Test(MarshmallowSchema):
    type = String(required=True)


class Sanitize(MarshmallowSchema):
    type = String(required=True)


class Snapshot_lite(Thing):
    uuid = String(required=True)
    version = String(required=True)
    schema_api = String(required=True)
    software = String(required=True)
    # software = EnumField(
    #     SnapshotSoftware,
    #     required=True,
    #     description='The software that generated this Snapshot.',
    # )
    sid = String(required=True)
    type = String(required=True)
    timestamp = String(required=True)
    settings_version = String(required=False)
    hwmd = Nested(Snapshot_lite_data, required=True)
    tests = Nested(Test, many=True, collection_class=list, required=False)
    sanitize = Nested(Sanitize, many=True, collection_class=list, required=False)

    @validates_schema
    def validate_workbench_version(self, data: dict):
        if data['schema_api'] not in app.config['SCHEMA_HWMD']:
            raise ValidationError(
                'Min. supported Workbench version is '
                '{} but yours is {}.'.format(
                    app.config['SCHEMA_HWMD'][0], data['version']
                ),
                field_names=['version'],
            )
