import logging
from smtplib import SMTPException
from threading import Thread
from flask import current_app
from flask_mail import Message, Mail

logger = logging.getLogger(__name__)


def _send_async_email(app, msg):
    with app.app_context():
        if not app.config['MAIL_SERVER']:
            logger.exception("Mail server is not config")
            return

        try:
            mail.send(msg)
        except SMTPException:
            logger.exception("Ocurrió un error al enviar el email")


def send_email(subject, sender, recipients, text_body,
               cc=None, bcc=None, html_body=None):

    msg = Message(
        subject,
        sender=sender,
        recipients=recipients,
        cc=cc,
        bcc=bcc
    )

    msg.body = text_body

    if html_body:
        msg.html = html_body

    Thread(
        target=_send_async_email,
        args=(current_app._get_current_object(), msg)
    ).start()


# from flask_mail import Message
# from ereuse_devicehub import mail
# msg = Message("Hola", sender="cayo@usody.com", recipients=["cayo@usody.com"]
# msg.body = "hola como te va?"
# mail.send(msg)
