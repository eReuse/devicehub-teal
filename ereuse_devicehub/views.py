import flask
from flask import Blueprint
from flask.views import View
from flask_login import login_required, login_user, logout_user

from ereuse_devicehub.forms import LoginForm
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.utils import is_safe_url

core = Blueprint('core', __name__)


class LoginView(View):
    methods = ['GET', 'POST']
    template_name = 'ereuse_devicehub/user_login.html'

    def dispatch_request(self):
        form = LoginForm()
        if form.validate_on_submit():
            # Login and validate the user.
            # user should be an instance of your `User` class
            user = User.query.filter_by(email=form.email.data).first()
            login_user(user)

            next_url = flask.request.args.get('next')
            # is_safe_url should check if the url is safe for redirects.
            # See http://flask.pocoo.org/snippets/62/ for an example.
            if not is_safe_url(flask.request, next_url):
                return flask.abort(400)

            return flask.redirect(next_url or flask.url_for('core.user-profile'))
        return flask.render_template('ereuse_devicehub/user_login.html', form=form)


class LogoutView(View):
    def dispatch_request(self):
        logout_user()
        return flask.redirect(flask.url_for('core.login'))


class UserProfileView(View):
    decorators = [login_required]
    template_name = 'ereuse_devicehub/user_profile.html'

    def dispatch_request(self):
        context = {}
        return flask.render_template(self.template_name, **context)


core.add_url_rule('/login/', view_func=LoginView.as_view('login'))
core.add_url_rule('/logout/', view_func=LogoutView.as_view('logout'))
core.add_url_rule('/profile/', view_func=UserProfileView.as_view('user-profile'))
