import json
import logging
import base64

import requests
from authlib.integrations.flask_oauth2 import current_token
from authlib.oauth2 import OAuth2Error
from flask import (
    Blueprint,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    current_app as app
)
from flask_login import login_required
from flask.views import View

from ereuse_devicehub import __version__, messages
from ereuse_devicehub.db import db
from ereuse_devicehub.modules.oidc.forms import (
    AuthorizeForm,
    CreateClientForm,
    ListInventoryForm,
)
from ereuse_devicehub.modules.oidc.models import (
    MemberFederated,
    OAuth2Client,
    Code2Roles
)
from ereuse_devicehub.modules.oidc.oauth2 import (
    authorization,
    generate_user_info,
    require_oauth,
)
from ereuse_devicehub.views import GenericMixin

oidc = Blueprint('oidc', __name__, url_prefix='/', template_folder='templates')
logger = logging.getLogger(__name__)


##########
# Server #
##########
class CreateClientView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'create_client.html'
    title = "Edit Open Id Connect Client"

    def dispatch_request(self):
        form = CreateClientForm()
        if form.validate_on_submit():
            form.save()
            next_url = url_for('core.user-profile')
            return redirect(next_url)

        self.get_context()
        self.context.update(
            {
                'form': form,
                'title': self.title,
            }
        )
        return render_template(self.template_name, **self.context)


class AuthorizeView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'authorize.html'
    title = "Authorize"

    def dispatch_request(self):
        form = AuthorizeForm()
        client = OAuth2Client.query.filter_by(
            client_id=request.args.get('client_id')
        ).first()
        if not client:
            messages.error('Not exist client')
            return redirect(url_for('core.user-profile'))

        if form.validate_on_submit():
            if not form.consent.data:
                return redirect(url_for('core.user-profile'))

            return authorization.create_authorization_response(grant_user=g.user)

        try:
            grant = authorization.validate_consent_request(end_user=g.user)
        except OAuth2Error as error:
            messages.error(error.error)
            return redirect(url_for('core.user-profile'))

        self.get_context()
        self.context.update(
            {'form': form, 'title': self.title, 'user': g.user, 'grant': grant}
        )
        return render_template(self.template_name, **self.context)


class IssueTokenView(GenericMixin):
    methods = ['POST']
    decorators = []

    def dispatch_request(self):
        return authorization.create_token_response()


class OauthProfileView(GenericMixin):
    methods = ['GET']
    decorators = []
    template_name = 'authorize.html'
    title = "Authorize"

    @require_oauth('profile')
    def dispatch_request(self):
        return jsonify(generate_user_info(current_token.user, current_token.scope))


##########
# Client #
##########
class SelectInventoryView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = []
    template_name = 'select_inventory.html'
    title = "Select an Inventory"

    def dispatch_request(self):
        host = app.config.get('HOST', '').strip("/")
        next = request.args.get('next', '#')
        # url = "https://ebsi-pcp-wallet-ui.vercel.app/oid4vp?"
        # url += f"client_id=https://{host}&"
        # url += "presentation_definition_uri=https://iotaledger.github.io"
        # url += "/ebsi-stardust-components/public/presentation-definition-ex1.json"
        # url += "/ebsi-stardust-components/public//presentation-definition-ereuse.json&"
        # url += f"response_uri=https://{host}/allow_code_oidc4vp"
        # url += "&state=1700822573400&response_type=vp_token&response_mode=direct_post"
        url = app.config.get('VERIFY_URL')
        url += f"?response_uri=http://{host}:5000/allow_code_oidc4vp"
        url += '&presentation_definition=["EOperatorClaim"]'

        session['next_url'] = next

        return redirect(url, code=302)


class AllowCodeView(GenericMixin):
    methods = ['GET', 'POST']
    decorators = []
    userinfo = None
    token = None
    discovery = {}

    def dispatch_request(self):
        self.code = request.args.get('code')
        self.oidc = session.get('oidc')
        if not self.code or not self.oidc:
            return self.redirect()

        self.member = MemberFederated.query.filter(
            MemberFederated.dlt_id_provider == self.oidc,
            MemberFederated.client_id.isnot(None),
            MemberFederated.client_secret.isnot(None),
        ).first()

        if not self.member:
            return self.redirect()

        self.get_token()
        if 'error' in self.token:
            messages.error(self.token.get('error', ''))
            return self.redirect()

        self.get_user_info()
        return self.redirect()

    def get_discovery(self):
        if self.discovery:
            return self.discovery

        try:
            url_well_known = self.member.domain + '.well-known/openid-configuration'
            self.discovery = requests.get(url_well_known).json()
        except Exception:
            self.discovery = {'code': 404}

        return self.discovery

    def get_token(self):
        data = {'grant_type': 'authorization_code', 'code': self.code}
        url = self.member.domain + '/oauth/token'
        url = self.get_discovery().get('token_endpoint', url)

        auth = (self.member.client_id, self.member.client_secret)
        msg = requests.post(url, data=data, auth=auth)
        self.token = json.loads(msg.text)

    def redirect(self):
        url = session.get('next_url') or '/login'
        return redirect(url)

    def get_user_info(self):
        if self.userinfo:
            return self.userinfo
        if 'access_token' not in self.token:
            return

        url = self.member.domain + '/oauth/userinfo'
        url = self.get_discovery().get('userinfo_endpoint', url)
        access_token = self.token['access_token']
        token_type = self.token.get('token_type', 'Bearer')
        headers = {"Authorization": f"{token_type} {access_token}"}

        msg = requests.get(url, headers=headers)
        self.userinfo = json.loads(msg.text)
        rols = self.userinfo.get('rols', [])
        session['rols'] = [(k, k) for k in rols]
        return self.userinfo


class AllowCodeOidc4vpView(GenericMixin):
    methods = ['POST']
    decorators = []
    userinfo = None
    token = None
    discovery = {}

    def dispatch_request(self):
        vcredential = self.get_credential()
        import pdb; pdb.set_trace()
        if not vcredential:
            return jsonify({"error": "No there are credentials"})

        roles = self.get_roles(vcredential)
        if not roles:
            return jsonify({"error": "No there are roles"})

        uri = self.get_response_uri(roles)

        return jsonify({"redirect_uri": uri})

    def get_credential(self):
        pv = request.values.get("vp_token")
        self.code = request.values.get("code")
        token = json.loads(base64.b64decode(pv).decode())
        return token.get("verifiableCredential")

    def get_roles(self, vps):
        try:
            for vp in vps:
                roles = vp.get('credentialSubject', {}).get('role')
                if roles:
                    return roles
        except Exception:
            roles = None
        return roles

    def get_response_uri(selfi, roles):
        code = Code2Roles(roles=roles)
        db.session.add(code)
        db.session.commit()

        url = "http://{host}/allow_code_oidc4vp2?code={code}".format(
            host=app.config.get('HOST'),
            code=code.code
        )
        return url


class AllowCodeOidc4vp2View(View):
    methods = ['GET', 'POST']

    def dispatch_request(self):
        self.code = request.args.get('code')
        if not self.code:
            return self.redirect()

        self.get_user_info()

        return self.redirect()

    def redirect(self):
        url = session.pop('next_url', '/login')
        return redirect(url)

    def get_user_info(self):
        import pdb; pdb.set_trace()
        code = Code2Roles.query.filter_by(code=self.code).first()

        if not code:
            return

        session['rols'] = [(k.strip(), k.strip()) for k in code.roles.split(",")]
        db.session.delete(code)
        db.session.commit()


##########
# Routes #
##########
oidc.add_url_rule('/create_client', view_func=CreateClientView.as_view('create_client'))
oidc.add_url_rule('/oauth/authorize', view_func=AuthorizeView.as_view('autorize_oidc'))
oidc.add_url_rule('/allow_code', view_func=AllowCodeView.as_view('allow_code'))
oidc.add_url_rule('/allow_code_oidc4vp', view_func=AllowCodeOidc4vpView.as_view('allow_code_oidc4vp'))
oidc.add_url_rule('/allow_code_oidc4vp2', view_func=AllowCodeOidc4vp2View.as_view('allow_code_oidc4vp2'))
oidc.add_url_rule('/oauth/token', view_func=IssueTokenView.as_view('oauth_issue_token'))
oidc.add_url_rule(
    '/oauth/userinfo', view_func=OauthProfileView.as_view('oauth_user_info')
)
oidc.add_url_rule(
    '/oidc/client/select',
    view_func=SelectInventoryView.as_view('login_other_inventory'),
)
