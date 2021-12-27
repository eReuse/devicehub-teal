from flask import Blueprint, render_template
from flask.views import View


core = Blueprint('core', __name__)


class LoginView(View):
    template_name = 'ereuse_devicehub/user_login.html'

    def dispatch_request(self):
        return render_template(self.template_name)


class UserProfileView(View):
    template_name = 'ereuse_devicehub/user_profile.html'

    def dispatch_request(self):
        return render_template(self.template_name)


core.add_url_rule('/login/', view_func=LoginView.as_view('login'))
core.add_url_rule('/profile/', view_func=UserProfileView.as_view('user-profile'))
