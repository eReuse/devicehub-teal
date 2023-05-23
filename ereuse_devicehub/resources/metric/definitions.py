from ereuse_devicehub.resources.metric.schema import Metric
from ereuse_devicehub.resources.metric.views import MetricsView
from ereuse_devicehub.teal.resource import Resource


class MetricDef(Resource):
    __type__ = 'Metric'
    VIEW = MetricsView
    SCHEMA = Metric
    AUTH = True
