import os
import time
from pathlib import Path

import flask
from flask import Blueprint
from flask import current_app as app
from flask import g, make_response, request
from flask_login import login_required

from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.enums import SessionType
from ereuse_devicehub.resources.user.models import Session
from ereuse_devicehub.views import GenericMixin

workbench = Blueprint('workbench', __name__, url_prefix='/workbench')


class SettingsView(GenericMixin):
    decorators = [login_required]
    template_name = 'workbench/settings.html'
    page_title = "Workbench"

    def dispatch_request(self):
        self.get_context()
        self.get_iso()
        self.context.update(
            {
                'page_title': self.page_title,
            }
        )

        self.opt = request.values.get('opt')
        if self.opt in ['register']:
            return self.download()

        return flask.render_template(self.template_name, **self.context)

    def get_iso(self):
        path = Path(__file__).parent.parent
        files = [
            f for f in os.listdir(f'{path}/static/iso/') if f[-3:].lower() == 'iso'
        ]

        self.context['2022_iso'] = ''
        self.context['2022_iso_sha'] = ''

        if files:
            self.context['iso'] = files[0]
            self.context['iso_sha'] = 'aaa'

    def download(self):
        url = "https://{}/api/inventory/".format(app.config['HOST'])
        self.wbContext = {
            'token': self.get_token(),
            'url': url,
        }
        options = {"register": self.register}
        return options[self.opt]()

    def register(self):
        data = flask.render_template('workbench/wbSettings.ini', **self.wbContext)
        return self.response_download(data)

    def response_download(self, data):
        bfile = str.encode(data)
        output = make_response(bfile)
        output.headers['Content-Disposition'] = 'attachment; filename=settings.ini'
        output.headers['Content-type'] = 'text/plain'
        return output

    def get_token(self):
        if not g.user.sessions:
            ses = Session(user=g.user)
            db.session.add(ses)
            db.session.commit()

        tk = ''
        now = time.time()
        for s in g.user.sessions:
            if s.type == SessionType.Internal and (s.expired == 0 or s.expired > now):
                tk = s.token
                break

        assert tk != ''

        token = auth.Auth.encode(tk)
        return token


workbench.add_url_rule('/', view_func=SettingsView.as_view('settings'))
