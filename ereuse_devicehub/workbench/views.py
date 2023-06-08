import time

import flask
from flask import Blueprint
from flask import current_app as app
from flask import g, make_response, request, url_for
from flask.views import View
from flask_login import login_required

from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Placeholder
from ereuse_devicehub.resources.enums import SessionType
from ereuse_devicehub.resources.user.models import Session
from ereuse_devicehub.views import GenericMixin
from ereuse_devicehub.workbench import isos
from ereuse_devicehub.workbench.forms import KangarooForm

workbench = Blueprint('workbench', __name__, url_prefix='/workbench')


class SettingsView(GenericMixin):
    decorators = [login_required]
    methods = ['GET', 'POST']
    template_name = 'workbench/settings.html'
    page_title = "Setup"

    def dispatch_request(self):
        self.get_context()
        form_kangaroo = KangarooForm()
        self.context.update(
            {
                'page_title': self.page_title,
                'demo': g.user.email == app.config['EMAIL_DEMO'],
                'iso_demo': isos['demo'],
                'iso_register': isos['register'],
                'iso_erease2': isos['erease2'],
                'iso_erease4': isos['erease4'],
                'form': form_kangaroo,
            }
        )

        if form_kangaroo.validate_on_submit():
            form_kangaroo.save()

        self.opt = request.values.get('opt')
        options = [
            'register',
            'erease_basic',
            'baseline_erease',
            'enhanced_erease',
        ]
        if self.opt in options:
            return self.download()

        return flask.render_template(self.template_name, **self.context)

    def download(self):
        url = "https://{}/api/inventory/".format(app.config['API_HOST'])
        self.wbContext = {
            'token': self.get_token(),
            'url': url,
            'erease_basic': None,
            'baseline_erease': None,
        }
        # if is a v14 version
        # TODO when not use more v14, we can remove this if
        template = 'workbench/wbSettings_BM.ini'
        if 'erease' in self.opt:
            url = "https://{}/actions/".format(app.config['API_HOST'])
            self.wbContext['url'] = url
            self.wbContext['host'] = app.config['HOST']
            self.wbContext['api_host'] = app.config['API_HOST']
            self.wbContext['schema'] = app.config['SCHEMA']

            if self.opt == 'erease_basic':
                template = 'workbench/wbSettings_BE.ini'
            if self.opt == 'baseline_erease':
                template = 'workbench/wbSettings_BSE.ini'
            if self.opt == 'enhanced_erease':
                template = 'workbench/wbSettings_ESE.ini'

        data = flask.render_template(template, **self.wbContext)
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


class ErasureHostView(View):
    decorators = [login_required]
    methods = ['GET']

    def dispatch_request(self, id):
        self.placeholder = (
            Placeholder.query.filter(Placeholder.id == id)
            .filter(Placeholder.kangaroo.is_(True))
            .filter(Placeholder.owner_id == g.user.id)
            .one()
        )
        self.placeholder.kangaroo = False
        db.session.commit()

        return flask.redirect(url_for('workbench.settings'))


workbench.add_url_rule('/', view_func=SettingsView.as_view('settings'))
workbench.add_url_rule(
    '/erasure_host/<int:id>/', view_func=ErasureHostView.as_view('erasure_host')
)
