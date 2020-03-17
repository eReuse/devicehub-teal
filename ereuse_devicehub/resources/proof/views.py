from distutils.version import StrictVersion
from typing import List
from uuid import UUID

from flask import current_app as app, request, jsonify
from sqlalchemy.util import OrderedSet
from teal.marshmallow import ValidationError
from teal.resource import View

from ereuse_devicehub.db import db
from ereuse_devicehub.query import things_response
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
        proofs = list()
        if json['batch']:
            for prf in json['proofs']:
                resource_def = app.resources[prf['type']]
                p = resource_def.schema.load(prf)
                Model = db.Model._decl_class_registry.data[prf['type']]()
                proof = Model(**p)
                db.session.add(proof)
                db.session.commit()
                proofs.append(self.schema.dump(proof))
            response = jsonify({
                'items': proofs,
                'url': request.path
            })
            response.status_code = 201
            return response
