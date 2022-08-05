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
        self.context.update(
            {
                'page_title': self.page_title,
                'demo': g.user.email == app.config['EMAIL_DEMO'],
            }
        )
        self.get_iso()

        self.opt = request.values.get('opt')
        if self.opt in ['register', 'erease_basic', 'erease_sectors']:
            return self.download()

        return flask.render_template(self.template_name, **self.context)

    def get_iso(self):
        path = Path(__file__).parent.parent
        uri = f'{path}/static/iso/'
        if self.context.get('demo'):
            uri = f'{path}/static/iso/demo/'

        self.context['iso'] = {}

        versions = os.listdir(f'{path}/static/iso/')
        versions.sort()

        for d in versions:
            dir_iso = f'{uri}/{d}'
            if not os.path.isdir(dir_iso):
                continue

            files = [f for f in os.listdir(dir_iso) if f[-3:].lower() == 'iso']

            if files:
                self.context['iso'][f'{d}'] = files[0]

    def download(self):
        url = "https://{}/api/inventory/".format(app.config['HOST'])
        self.wbContext = {
            'token': self.get_token(),
            'url': url,
            'erease_basic': None,
            'erease_sectors': None,
        }
        # if is a v14 version
        # TODO when not use more v14, we can remove this if
        if 'erease' in self.opt:
            url = "https://{}/actions/".format(app.config['HOST'])
            self.wbContext['url'] = url
            if self.opt == 'erease_basic':
                self.wbContext['erease_basic'] = True
            if self.opt == 'erease_sectors':
                self.wbContext['erease_sectors'] = True

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
