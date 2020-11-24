from flask import request, g, jsonify
from ereuse_devicehub.resources.action import schemas
from teal.resource import Resource, View

from ereuse_devicehub.resources.action.models import Allocate, Live, Action, ToRepair, ToPrepare
from ereuse_devicehub.resources.device import models as m
from ereuse_devicehub.resources.metric.schema import Metric


class MetricsView(View):
    def find(self, args: dict):

        self.params = dict(request.args)
        unvalid = self.schema.validate(self.params)
        if unvalid:
            res = jsonify(unvalid)
            res.status = 404
            return res

        metrics = {
                "allocateds": self.allocated(),
                "live": self.live(),
                "null": self.nulls(),
        }
        return jsonify(metrics)

    def allocated(self):
        return Allocate.query.filter(
            Allocate.start_time.between(
                self.params['start_time'], self.params['end_time']
                ),
            Action.author==g.user
        ).count()

    def live(self):
        return Live.query.filter(
            Live.created.between(
                self.params['start_time'], self.params['end_time']
                ),
            Action.author==g.user
        ).distinct(Live.serial_number).count()

    def nulls(self):
        to_repair = ToRepair.query.filter(
            ToRepair.created.between(
                self.params['start_time'], self.params['end_time']
                ),
            Action.author==g.user
        ).count()
        to_prepare = ToPrepare.query.filter(
            ToPrepare.created.between(
                self.params['start_time'], self.params['end_time']
                ),
            Action.author==g.user
        ).count()
        return to_repair + to_prepare


class MetricDef(Resource):
    __type__ = 'Metric'
    VIEW = MetricsView
    SCHEMA = Metric
    AUTH = True
