from flask import Blueprint

core = Blueprint('core', __name__)


@core.route('/profile/')
def user_profile():
    return "Hello world!"
