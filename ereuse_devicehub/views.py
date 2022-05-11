import flask
from flask import Blueprint, g
from flask.views import View
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from ereuse_devicehub import __version__, messages
from ereuse_devicehub.db import db
from ereuse_devicehub.forms import LoginForm, PasswordForm
from ereuse_devicehub.resources.action.models import Trade
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.utils import is_safe_url

core = Blueprint('core', __name__)


@core.route("/")
def index():
    return flask.redirect(flask.url_for('core.login'))


class LoginView(View):
    methods = ['GET', 'POST']
    template_name = 'ereuse_devicehub/user_login.html'

    def dispatch_request(self):
        form = LoginForm()
        if form.validate_on_submit():
            # Login and validate the user.
            # user should be an instance of your `User` class
            user = User.query.filter_by(email=form.email.data).first()
            login_user(user, remember=form.remember.data)

            next_url = flask.request.args.get('next')
            # is_safe_url should check if the url is safe for redirects.
            # See http://flask.pocoo.org/snippets/62/ for an example.
            if not is_safe_url(flask.request, next_url):
                return flask.abort(400)

            return flask.redirect(next_url or flask.url_for('inventory.devicelist'))
        context = {'form': form, 'version': __version__}
        return flask.render_template('ereuse_devicehub/user_login.html', **context)


class LogoutView(View):
    def dispatch_request(self):
        logout_user()
        return flask.redirect(flask.url_for('core.login'))


class GenericMixView(View):
    decorators = [login_required]

    def get_lots(self):
        return (
            Lot.query.outerjoin(Trade)
            .filter(
                or_(
                    Trade.user_from == g.user,
                    Trade.user_to == g.user,
                    Lot.owner_id == g.user.id,
                )
            )
            .distinct()
        )

    def get_context(self):
        self.context = {
            'lots': self.get_lots(),
            'version': __version__,
        }

        return self.context


class UserProfileView(GenericMixView):
    decorators = [login_required]
    template_name = 'ereuse_devicehub/user_profile.html'

    def dispatch_request(self):
        self.get_context()
        self.context.update(
            {
                'current_user': current_user,
                'password_form': PasswordForm(),
            }
        )

        return flask.render_template(self.template_name, **self.context)


class UserPasswordView(View):
    methods = ['POST']
    decorators = [login_required]

    def dispatch_request(self):
        form = PasswordForm()
        db.session.commit()
        if form.validate_on_submit():
            form.save(commit=False)
            messages.success('Reset user password successfully!')
        else:
            messages.error('Error modifying user password!')

        db.session.commit()
        return flask.redirect(flask.url_for('core.user-profile'))


core.add_url_rule('/login/', view_func=LoginView.as_view('login'))
core.add_url_rule('/logout/', view_func=LogoutView.as_view('logout'))
core.add_url_rule('/profile/', view_func=UserProfileView.as_view('user-profile'))
core.add_url_rule('/set_password/', view_func=UserPasswordView.as_view('set-password'))
