from flask import Blueprint, render_template

core = Blueprint('core', __name__)


@core.route('/profile/')
def user_profile():
    return render_template('ereuse_devicehub/user_profile.html')
