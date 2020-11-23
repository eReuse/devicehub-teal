from flask import request, g, jsonify
from ereuse_devicehub.resources.action import schemas
from teal.resource import Resource, View

from ereuse_devicehub.resources.action.models import Allocate
from ereuse_devicehub.resources.device import models as m
from ereuse_devicehub.resources.metric.schema import Metric


class MetricsView(View):
    def find(self, args: dict):
        self.params = request.get_json()
        metrics = {
                "allocateds": self.allocated(),
                "live": 0,
                "null": 0,
        }
        return jsonify(metrics)

    def allocated(self):
        return Allocate.query.filter(
                Allocate.start_time.between(
                    self.params['start_time'], self.params['end_time']
                )
        ).count()


class MetricDef(Resource):
    __type__ = 'Metric'
    VIEW = MetricsView
    SCHEMA = Metric
    AUTH = True
