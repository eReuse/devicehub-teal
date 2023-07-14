from datetime import datetime

from flask import current_app as app
from marshmallow import Schema as MarshmallowSchema
from marshmallow import ValidationError, pre_load, validates_schema
from marshmallow.fields import DateTime, Dict, Integer, List, Nested, String
from marshmallow_enum import EnumField

from ereuse_devicehub.resources.enums import Severity, SnapshotSoftware
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


class Steps(MarshmallowSchema):
    num = Integer(data_key='step', required=True)
    start_time = DateTime(data_key='date_init', required=True)
    end_time = DateTime(data_key='date_end', required=True)
    severity = EnumField(Severity)

    @pre_load
    def preload_datas(self, data: dict):
        data['severity'] = Severity.Info.name

        if not data.pop('success', False):
            data['severity'] = Severity.Error.name
        data.pop('duration', None)
        data.pop('commands', None)

        if data.get('date_init'):
            data['date_init'] = datetime.fromtimestamp(data['date_init']).isoformat()
            data['date_end'] = datetime.fromtimestamp(data['date_end']).isoformat()


class Sanitize(MarshmallowSchema):
    steps = Nested(Steps, many=True, required=True, data_key='erasure_steps')
    validation = Dict()
    device_info = Dict()
    method = Dict(required=True)
    sanitize_version = String()
    severity = EnumField(Severity, required=True)

    @pre_load
    def preload_datas(self, data: dict):
        data['severity'] = Severity.Info.name

        if not data.pop('result', False):
            data['severity'] = Severity.Error.name


class Snapshot_lite(Thing):
    uuid = String(required=True)
    version = String(required=True)
    schema_api = String(required=True)
    software = EnumField(
        SnapshotSoftware,
        required=True,
        description='The software that generated this Snapshot.',
    )
    sid = String(required=True)
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
