from typing import Callable, Iterable, Tuple

from ereuse_devicehub.resources.deliverynote import schemas
from ereuse_devicehub.resources.deliverynote.views import DeliverynoteView
from ereuse_devicehub.teal.resource import Converters, Resource


class DeliverynoteDef(Resource):
    SCHEMA = schemas.Deliverynote
    VIEW = DeliverynoteView
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
