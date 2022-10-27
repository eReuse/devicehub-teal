import flask
from flask import Blueprint
from flask.views import View

from ereuse_devicehub import __version__
from ereuse_devicehub.db import db
from ereuse_devicehub.register.forms import UserNewRegisterForm
from ereuse_devicehub.resources.user.models import UserValidation

register = Blueprint('register', __name__, template_folder='templates')


class UserRegistrationView(View):
    methods = ['GET', 'POST']
    template_name = 'registration/user_registration.html'

    def dispatch_request(self):
        form = UserNewRegisterForm()
        if form.validate_on_submit():
            form.save()
        context = {'form': form, 'version': __version__}
        return flask.render_template(self.template_name, **context)


class UserValidationView(View):
    methods = ['GET']
    template_name = 'registration/user_validation.html'

    def dispatch_request(self, token):
        context = {'is_valid': self.is_valid(token), 'version': __version__}
        return flask.render_template(self.template_name, **context)

    def is_valid(self, token):
        user_valid = UserValidation.query.filter_by(token=token).first()
        if not user_valid:
            return False
        user = user_valid.user
        user.active = True
        db.session.commit()
        return True


register.add_url_rule(
    '/new_register/',
    view_func=UserRegistrationView.as_view('user-registration'),
)
register.add_url_rule(
    '/validate_user/<uuid:token>',
    view_func=UserValidationView.as_view('user-validation'),
)
