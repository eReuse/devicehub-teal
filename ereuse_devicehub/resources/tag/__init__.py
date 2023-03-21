import csv
import pathlib

from click import argument, option
from ereuse_devicehub.ereuse_utils import cli

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.definitions import DeviceDef
from ereuse_devicehub.resources.tag import schema
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.resources.tag.view import (
    TagDeviceView,
    TagView,
    get_device_from_tag,
)
from ereuse_devicehub.teal.resource import Converters, Resource
from ereuse_devicehub.teal.teal import Teal


class TagDef(Resource):
    SCHEMA = schema.Tag
    VIEW = TagView
    ID_CONVERTER = Converters.lower

    OWNER_H = 'The id of the user who owns this tag. '
    ORG_H = 'The name of an existing organization in the DB. '
    'By default the organization operating this Devicehub.'
    PROV_H = 'The Base URL of the provider; scheme + domain. Ex: "https://foo.com". '
    'By default set to the actual Devicehub.'
    CLI_SCHEMA = schema.Tag(only=('id', 'provider', 'org', 'secondary'))

    def __init__(
        self,
        app: Teal,
        import_name=__name__.split('.')[0],
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
    ):
        cli_commands = ((self.create_tag, 'add'), (self.create_tags_csv, 'add-csv'))
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

        # DeviceTagView URLs
        device_view = TagDeviceView.as_view(
            'tag-device-view', definition=self, auth=app.auth
        )
        if self.AUTH:
            device_view = app.auth.requires_auth(device_view)
        self.add_url_rule(
            '/<{0.ID_CONVERTER.value}:{0.ID_NAME}>/device'.format(self),
            view_func=device_view,
            methods={'GET'},
        )
        self.add_url_rule(
            '/<{0.ID_CONVERTER.value}:tag_id>/'.format(self)
            + 'device/<{0.ID_CONVERTER.value}:device_id>'.format(DeviceDef),
            view_func=device_view,
            methods={'PUT'},
        )
        self.add_url_rule(
            '/<{0.ID_CONVERTER.value}:tag_id>/'.format(self)
            + 'device/<{0.ID_CONVERTER.value}:device_id>'.format(DeviceDef),
            view_func=device_view,
            methods={'DELETE'},
        )

    @option('-u', '--owner', help=OWNER_H)
    @option('-o', '--org', help=ORG_H)
    @option('-p', '--provider', help=PROV_H)
    @option('-s', '--sec', help=Tag.secondary.comment)
    @argument('id')
    def create_tag(
        self,
        id: str,
        org: str = None,
        owner: str = None,
        sec: str = None,
        provider: str = None,
    ):
        """Create a tag with the given ID."""
        db.session.add(
            Tag(
                **self.schema.load(
                    dict(id=id, owner=owner, org=org, secondary=sec, provider=provider)
                )
            )
        )
        db.session.commit()

    @option('-u', '--owner', help=OWNER_H)
    @option('--org', help=ORG_H)
    @option('--provider', help=PROV_H)
    @argument('path', type=cli.Path(writable=True))
    def create_tags_csv(self, path: pathlib.Path, owner: str, org: str, provider: str):
        """Creates tags by reading CSV from ereuse-tag.

        CSV must have the following columns:

        1. ID tag
        2. Secondary id tag (or empty)
        """
        with path.open() as f:
            for id, sec in csv.reader(f):
                db.session.add(
                    Tag(
                        **self.schema.load(
                            dict(
                                id=id,
                                owner=owner,
                                org=org,
                                secondary=sec,
                                provider=provider,
                            )
                        )
                    )
                )
        db.session.commit()
