import flask
from decouple import config
from flask import Blueprint
from flask import current_app as app
from flask import g, session
from flask.views import View
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from ereuse_devicehub import __version__, messages
from ereuse_devicehub.db import db
from ereuse_devicehub.forms import LoginForm, PasswordForm, SanitizationEntityForm
from ereuse_devicehub.resources.action.models import Trade
from ereuse_devicehub.resources.lot.models import Lot, ShareLot
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

        url_register = "#"
        url_reset_password = "#"

        if 'register' in app.blueprints.keys():
            url_register = config("PRICES_PAGE", "#")

        if 'reset_password' in app.blueprints.keys():
            url_reset_password = flask.url_for('reset_password.reset-password')

        context = {
            'form': form,
            'version': __version__,
            'url_register': url_register,
            'url_reset_password': url_reset_password,
        }

        return flask.render_template(self.template_name, **context)


class LogoutView(View):
    def dispatch_request(self):
        session_vars = ['token_dlt', 'rols', 'oidc']
        [session.pop(i, '') for i in session_vars]
        next_url = flask.request.args.get('next')
        logout_user()
        return flask.redirect(next_url or flask.url_for('core.login'))


class GenericMixin(View):
    methods = ['GET']
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
            'share_lots': ShareLot.query.filter_by(user_to=g.user),
        }

        return self.context


class UserProfileView(GenericMixin):
    decorators = [login_required]
    template_name = 'ereuse_devicehub/user_profile.html'

    def dispatch_request(self):
        self.get_context()
        sanitization_form = SanitizationEntityForm()
        if g.user.sanitization_entity:
            sanitization = g.user.sanitization_entity
            sanitization_form = SanitizationEntityForm(obj=sanitization)
        oidc = 'oidc' in app.blueprints.keys()
        self.context.update(
            {
                'current_user': current_user,
                'password_form': PasswordForm(),
                'sanitization_form': sanitization_form,
                'oidc': oidc,
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


class SanitizationEntityView(View):
    methods = ['POST']
    decorators = [login_required]

    def dispatch_request(self):
        form = SanitizationEntityForm()
        if form.validate_on_submit():
            form.save()
            messages.success('Sanitization data updated successfully!')
        else:
            messages.error('Error modifying Sanitization data!')
            if form.errors:
                for k in form.errors.keys():
                    errors = ", ".join(form.errors[k])
                    txt = "{}: {}".format(k, errors)
                    messages.error(txt)

        return flask.redirect(flask.url_for('core.user-profile'))


core.add_url_rule('/login/', view_func=LoginView.as_view('login'))
core.add_url_rule('/logout/', view_func=LogoutView.as_view('logout'))
core.add_url_rule('/profile/', view_func=UserProfileView.as_view('user-profile'))
core.add_url_rule('/set_password/', view_func=UserPasswordView.as_view('set-password'))
core.add_url_rule(
    '/set_sanitization/', view_func=SanitizationEntityView.as_view('set-sanitization')
)
