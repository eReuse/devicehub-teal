from typing import Callable, Iterable, Tuple

from flask.json import jsonify

from ereuse_devicehub.teal.resource import Resource, View


class LicenceView(View):
    def get(self, *args, **kwargs):
        """Get version of DeviceHub and ereuse-tag."""

        app = self.resource_def.app
        path_licences = app.config['LICENCES']
        with open(path_licences) as f:
            licences = f.read()

        ret = jsonify(licences)
        ret.status_code = 200
        return ret


class LicencesDef(Resource):
    __type__ = 'Licence'
    SCHEMA = None
    VIEW = None  # We do not want to create default / documents endpoint
    AUTH = False

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
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

        get = {'GET'}
        d = {}

        licence_view = LicenceView.as_view('LicenceView', definition=self)
        self.add_url_rule('/', defaults=d, view_func=licence_view, methods=get)
