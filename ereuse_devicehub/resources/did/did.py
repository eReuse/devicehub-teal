from typing import Callable, Iterable, Tuple

from flask import redirect, url_for

from ereuse_devicehub.teal.resource import Resource, View


class DidView(View):
    """
    This view render one public ans static page for see the links for to do the check
    of one csv file
    """

    def get(self, dpp: str):
        return redirect(url_for('did.did', id_dpp=dpp))


class DidDef(Resource):
    __type__ = 'Did'
    SCHEMA = None
    VIEW = None  # We do not want to create default / documents endpoint
    AUTH = False

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder='static',
        static_url_path=None,
        template_folder='templates',
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )

        # view = DidView.as_view('main', definition=self, auth=app.auth)

        # if self.AUTH:
        #     view = app.auth.requires_auth(view)

        did_view = DidView.as_view('DidView', definition=self, auth=app.auth)
        self.add_url_rule(
            '/<string:dpp>', defaults={}, view_func=did_view, methods={'GET'}
        )
