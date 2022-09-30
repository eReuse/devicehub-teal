from flask import g
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash
from wtforms import (
    BooleanField,
    EmailField,
    PasswordField,
    StringField,
    TelField,
    validators,
)

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.user.models import User, UserValidation


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
        g.user.password = self.newpassword.data

        db.session.add(g.user)
        if commit:
            db.session.commit()
        return


class UserNewRegisterForm(FlaskForm):
    email = EmailField(
        'Email Address', [validators.DataRequired(), validators.Length(min=6, max=35)]
    )
    password = PasswordField('Password', [validators.DataRequired()])
    password2 = PasswordField('Password', [validators.DataRequired()])
    name = StringField(
        'Name', [validators.DataRequired(), validators.Length(min=3, max=35)]
    )
    telephone = TelField('Telephone', [validators.DataRequired()])

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
        password2 = self.password2.data
        if password != password2:
            self.form_errors.append('The passwords are not equal.')
            return False

        txt = 'This email are in use.'
        email = self.email.data
        if User.query.filter_by(email=email).first():
            self.form_errors.append(txt)
            return False

        return True

    def save(self, commit=True):
        user = User(email=self.email.data, password=self.password.data, active=False)

        person = Person(
            email=self.email.data, name=self.name.data, telephone=self.telephone.data
        )

        user.individuals.add(person)
        db.session.add(user)

        user_validation = UserValidation(
            user=user,
        )
        self._token = user_validation.token
        db.session.add(user_validation)

        if commit:
            db.session.commit()
