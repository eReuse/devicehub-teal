from flask import current_app as app
from flask import render_template
from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField, validators

from ereuse_devicehub.db import db
from ereuse_devicehub.mail.sender import send_email
from ereuse_devicehub.resources.agent.models import Person
from ereuse_devicehub.resources.user.models import User, UserValidation


class UserNewRegisterForm(FlaskForm):
    email = EmailField(
        'Email Address', [validators.DataRequired(), validators.Length(min=6, max=35)]
    )
    password = PasswordField(
        'Password', [validators.DataRequired(), validators.Length(min=6, max=35)]
    )
    password2 = PasswordField(
        'Password', [validators.DataRequired(), validators.Length(min=6, max=35)]
    )
    name = StringField(
        'Name', [validators.DataRequired(), validators.Length(min=3, max=35)]
    )

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

        self.email.data = self.email.data.strip()
        self.password.data = self.password.data.strip()

        return True

    def save(self, commit=True):
        user_validation = self.new_user()
        if commit:
            db.session.commit()

        self._token = user_validation.token
        self.send_mail()
        self.send_mail_admin(user_validation.user)

    def new_user(self):
        user = User(email=self.email.data, password=self.password.data, active=False)

        person = Person(
            email=self.email.data,
            name=self.name.data,
        )

        user.individuals.add(person)
        db.session.add(user)

        user_validation = UserValidation(
            user=user,
        )
        db.session.add(user_validation)

        return user_validation

    def send_mail(self):
        host = app.config.get('HOST')
        token = self._token
        url = f'https://{ host }/validate_user/{ token }'
        template = 'registration/email_validation.txt'
        template_html = 'registration/email_validation.html'
        context = {
            'name': self.name.data,
            'host': host,
            'url': url,
        }
        subject = "Please activate your Usody account"
        message = render_template(template, **context)
        message_html = render_template(template_html, **context)

        send_email(subject, [self.email.data], message, html_body=message_html)

    def send_mail_admin(self, user):
        person = next(iter(user.individuals))
        context = {
            'email': person.email,
            'name': person.name,
        }
        template = 'registration/email_admin_new_user.txt'
        message = render_template(template, **context)
        subject = "New Register"

        email_admin = app.config.get("EMAIL_ADMIN")
        if email_admin:
            send_email(subject, [email_admin], message)
