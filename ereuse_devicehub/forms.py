from flask import current_app as app
from flask import g, session
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash
from wtforms import BooleanField, EmailField, PasswordField, validators

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.user.models import User


class LoginForm(FlaskForm):
    email = EmailField('Email Address', [validators.Length(min=6, max=35)])
    password = PasswordField('Password', [validators.DataRequired()])
    remember = BooleanField('Remember me')

    error_messages = {
        'invalid_login': (
            "Please enter a correct email and password. Note that both "
            "fields may be case-sensitive."
        ),
        'inactive': "This account is inactive.",
    }

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            return False

        email = self.email.data
        password = self.password.data
        self.user_cache = self.authenticate(email, password)

        if self.user_cache is None:
            self.form_errors.append(self.error_messages['invalid_login'])
            return False

        return self.confirm_login_allowed(self.user_cache)

    def authenticate(self, email, password):
        if email is None or password is None:
            return
        user = User.query.filter_by(email=email).first()
        if user is None:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            generate_password_hash(password)
        else:
            if user.check_password(password):
                return user

    def confirm_login_allowed(self, user):
        """
        Controls whether the given User may log in. This is a policy setting,
        independent of end-user authentication. This default behavior is to
        allow login by active users, and reject login by inactive users.
        If the given user cannot log in, this method should raise a
        ``ValidationError``.
        If the given user may log in, this method should return None.
        """
        if not user.is_active:
            self.form_errors.append(self.error_messages['inactive'])

        if 'trublo' in app.blueprints.keys():
            token_dlt = (
                user.get_dlt_keys(self.password.data).get('data', {}).get('api_token')
            )
            session['token_dlt'] = token_dlt

        return user.is_active


class PasswordForm(FlaskForm):
    password = PasswordField(
        'Current Password',
        [validators.DataRequired()],
        render_kw={'class': "form-control"},
    )
    newpassword = PasswordField(
        'New Password',
        [validators.DataRequired()],
        render_kw={'class': "form-control"},
    )
    renewpassword = PasswordField(
        'Re-enter New Password',
        [validators.DataRequired()],
        render_kw={'class': "form-control"},
    )

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)

        if not is_valid:
            return False

        if not g.user.check_password(self.password.data):
            return False

        if self.newpassword.data != self.renewpassword.data:
            return False

        return True

    def save(self, commit=True):
        if 'trublo' not in app.blueprints.keys():
            keys_dlt = g.user.get_dlt_keys(self.password.data)
            g.user.reset_dlt_keys(self.newpassword.data, keys_dlt)

            token_dlt = (
                user.get_dlt_keys(self.password.data).get('data', {}).get('api_token')
            )
            session['token_dlt'] = token_dlt

        g.user.password = self.newpassword.data

        db.session.add(g.user)
        if commit:
            db.session.commit()
        return
