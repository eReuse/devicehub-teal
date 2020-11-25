from flask import request, g, jsonify
from contextlib import suppress
from teal.resource import View

from ereuse_devicehub.resources.action import schemas
from ereuse_devicehub.resources.action.models import Allocate, Live, Action, ToRepair, ToPrepare
from ereuse_devicehub.resources.device import models as m
from ereuse_devicehub.resources.metric.schema import Metric


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
            live = allocate = None
            with suppress(LookupError):
                live = dev.last_action_of(Live)
            with suppress(LookupError):
                allocate = dev.last_action_of(Allocate)

            if not live:
                continue
            if allocate and allocate.created > live.created:
                continue
            count += 1

        return count

