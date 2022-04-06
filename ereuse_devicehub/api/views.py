from binascii import Error as asciiError

from flask import Blueprint, jsonify, request
from flask.views import View
from werkzeug.exceptions import Unauthorized

from ereuse_devicehub.auth import Auth

api = Blueprint('api', __name__, url_prefix='/api')


class LoginMix(View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.authenticate()

    def authenticate(self):
        unauthorized = Unauthorized('Provide a suitable token.')
        basic_token = request.headers.get('Authorization', " ").split(" ")
        if not len(basic_token) == 2:
            raise unauthorized

        token = basic_token[1]
        try:
            token = Auth.decode(token)
        except asciiError:
            raise unauthorized
        self.user = Auth().authenticate(token)


class InventoryView(LoginMix):
    methods = ['POST']

    def dispatch_request(self):
        return jsonify("Ok")


api.add_url_rule('/inventory/', view_func=InventoryView.as_view('inventory'))
