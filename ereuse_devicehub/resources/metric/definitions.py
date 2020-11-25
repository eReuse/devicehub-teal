from teal.resource import Resource
from ereuse_devicehub.resources.metric.schema import Metric
from ereuse_devicehub.resources.metric.views import MetricsView


class MetricDef(Resource):
    __type__ = 'Metric'
    VIEW = MetricsView
    SCHEMA = Metric
    AUTH = True
