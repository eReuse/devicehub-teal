import pathlib
from typing import Callable, Iterable, Tuple

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.lot import schemas
from ereuse_devicehub.resources.lot.views import (
    LotBaseChildrenView,
    LotChildrenView,
    LotDeviceView,
    LotView,
)
from ereuse_devicehub.teal.resource import Converters, Resource


class LotDef(Resource):
    SCHEMA = schemas.Lot
    VIEW = LotView
    AUTH = True
    ID_CONVERTER = Converters.uuid

    def __init__(
        self,
        app,
        import_name=__name__.split('.')[0],
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
        lot_children = LotChildrenView.as_view(
            'lot-children', definition=self, auth=app.auth
        )
        if self.AUTH:
            lot_children = app.auth.requires_auth(lot_children)
        self.add_url_rule(
            '/<{}:{}>/children'.format(self.ID_CONVERTER.value, self.ID_NAME),
            view_func=lot_children,
            methods={'POST', 'DELETE'},
        )
        lot_device = LotDeviceView.as_view('lot-device', definition=self, auth=app.auth)
        if self.AUTH:
            lot_device = app.auth.requires_auth(lot_device)
        self.add_url_rule(
            '/<{}:{}>/devices'.format(self.ID_CONVERTER.value, self.ID_NAME),
            view_func=lot_device,
            methods={'POST', 'DELETE'},
        )

    def init_db(self, db: 'db.SQLAlchemy', exclude_schema=None):
        # Create functions
        with pathlib.Path(__file__).parent.joinpath('dag.sql').open() as f:
            sql = f.read()
            db.session.execute(sql)
