from distutils.version import StrictVersion

from flask import current_app as app, request, jsonify
from teal.marshmallow import ValidationError
from teal.resource import View

from ereuse_devicehub.db import db

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
                proofs.append(resource_def.schema.dump(proof))
            db.session().final_flush()
            db.session.commit()
            response = jsonify({
                'items': proofs,
                'url': request.path
            })
            response.status_code = 201
            return response
