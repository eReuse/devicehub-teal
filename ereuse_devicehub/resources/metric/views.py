from flask import request, g, jsonify
from ereuse_devicehub.resources.action import schemas
from teal.resource import View

from ereuse_devicehub.resources.action.models import Allocate, Live, Action, ToRepair, ToPrepare
from ereuse_devicehub.resources.device import models as m
from ereuse_devicehub.resources.metric.schema import Metric


def last_action(dev, action):
    act = [e for e in reversed(dev.actions) if isinstance(e, action)]
    return act[0] if act else None 


class MetricsView(View):
    def find(self, args: dict):

        metrics = {
                "allocateds": self.allocated(),
                "live": self.live(),
        }
        return jsonify(metrics)

    def allocated(self):
        # TODO @cayop we need uncomment when the pr/83 is approved
        # return m.Device.query.filter(m.Device.allocated==True, owner==g.user).count()
        return m.Device.query.filter(m.Device.allocated==True).count()

    def live(self):
        # TODO @cayop we need uncomment when the pr/83 is approved
        # devices = m.Device.query.filter(m.Device.allocated==True, owner==g.user)
        devices = m.Device.query.filter(m.Device.allocated==True)
        count = 0
        for dev in devices:
            live = last_action(dev, Live)
            allocate = last_action(dev, Allocate)
            if not live:
                continue
            if allocate and allocate.created > live.created:
                continue
            count += 1

        return count

