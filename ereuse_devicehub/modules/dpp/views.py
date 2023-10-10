import json

from flask import Blueprint
from flask.views import View
from .models import Proof, Dpp, ALGORITHM

dpp = Blueprint('dpp', __name__, url_prefix='/', template_folder='templates')


class ProofView(View):
    methods = ['GET']

    def dispatch_request(selfi, proof_id):
        proof = Proof.query.filter_by(timestamp=proof_id).first()

        if not proof:
            proof = Dpp.query.filter_by(timestamp=proof_id).one()
            document = proof.snapshot.json_hw
        else:
            document = proof.normalizeDoc

        data = {
            "algorithm": ALGORITHM,
            "document": document
        }

        d = {
            '@context': ['https://ereuse.org/proof0.json'],
            'data': data,
        }

        return json.dumps(d)


##########
# Routes #
##########
dpp.add_url_rule('/proofs/<int:proof_id>', view_func=ProofView.as_view('proof'))
