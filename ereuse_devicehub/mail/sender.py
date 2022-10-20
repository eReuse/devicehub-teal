import logging
from smtplib import SMTPException
from threading import Thread

from flask import current_app as app

from ereuse_devicehub.mail.flask_mail import Message

logger = logging.getLogger(__name__)


def _send_async_email(app, msg):
    with app.app_context():
        try:
            app.mail.send(msg)
        except SMTPException:
            logger.exception("An error occurred while sending the email")


def send_email(
    subject, recipients, text_body, sender=None, cc=None, bcc=None, html_body=None
):

    msg = Message(subject, sender=sender, recipients=recipients, cc=cc, bcc=bcc)

    msg.body = text_body

    if html_body:
        msg.html = html_body

    Thread(target=_send_async_email, args=(app._get_current_object(), msg)).start()
