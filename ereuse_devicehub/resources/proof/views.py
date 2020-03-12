from distutils.version import StrictVersion
from typing import List
from uuid import UUID

from flask import current_app as app, request
from sqlalchemy.util import OrderedSet
from teal.marshmallow import ValidationError
from teal.resource import View

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import Action, RateComputer, Snapshot, VisualTest
from ereuse_devicehub.resources.action.rate.v1_0 import CannotRate
from ereuse_devicehub.resources.device.models import Component, Computer
from ereuse_devicehub.resources.enums import SnapshotSoftware

SUPPORTED_WORKBENCH = StrictVersion('11.0')


class ProofView(View):
    def post(self):
        """Posts batches of proofs."""
        json = request.get_json(validate=False)
        if not json:
            raise ValidationError('JSON is not correct.')
        # todo there should be a way to better get subclassess resource
        #   defs
        if json['batch']:
            for proof in json['proofs']:
                resource_def = app.resources[proof['type']]
                a = resource_def.schema.load(json)
                Model = db.Model._decl_class_registry.data[json['type']]()
                action = Model(**a)
                db.session.add(action)
                db.session().final_flush()
                ret = self.schema.jsonify(action)
            db.session.commit()
            ret.status_code = 201
            return ret
