import logging

import flask
from flask import Blueprint
from flask.views import View
from flask_login import current_user, login_required
from sqlalchemy.sql import extract

from ereuse_devicehub import __version__
from ereuse_devicehub.resources.action.models import Snapshot

billing = Blueprint(
    "billing", __name__, url_prefix="/billing", template_folder="templates"
)

logger = logging.getLogger(__name__)


class BillingIndexView(View):
    methods = ["GET"]
    decorators = [login_required]
    template_name = "billing/home.html"

    def dispatch_request(self):
        # TODO (@slamora): replace hardcoded and get current time
        # https://dateutil.readthedocs.io/en/stable/_modules/dateutil/tz/tz.html?highlight=now()
        #        datetime.now(tzutc())
        year = 2022
        month = 9
        snapshot_register, snapshot_update = self.count_snapshot(year, month)

        current_month_usage = {
            "year": year,
            "month": month,
            "snapshot_register": snapshot_register,
            "snapshot_update": snapshot_update,
            # TODO (@slamora): data erasure count
        }
        context = {
            "current_month_usage": current_month_usage,
            "page_title": "Billing",
            "version": __version__,
        }
        return flask.render_template(self.template_name, **context)

    def count_snapshot(self, year, month):
        query = Snapshot.query.filter(
            Snapshot.author_id == current_user.id,
            extract('year', Snapshot.created) == year,
            extract('month', Snapshot.created) == month,
        )

        all = query.count()
        register = query.distinct(Snapshot.device_id).count()
        update = all - register

        return (register, update)


billing.add_url_rule("/", view_func=BillingIndexView.as_view("billing_index"))
