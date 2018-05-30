from typing import Tuple

from click import argument, option

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.tag.model import Tag
from ereuse_devicehub.resources.tag.schema import Tag as TagS
from ereuse_devicehub.resources.tag.view import TagView, get_device_from_tag
from teal.resource import Resource
from teal.teal import Teal


class TagDef(Resource):
    SCHEMA = TagS
    VIEW = TagView

    def __init__(self, app: Teal, import_name=__package__, static_folder=None,
                 static_url_path=None,
                 template_folder=None, url_prefix=None, subdomain=None, url_defaults=None,
                 root_path=None):
        cli_commands = (
            (self.create_tags, 'create-tags'),
        )
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)
        _get_device_from_tag = app.auth.requires_auth(get_device_from_tag)
        self.add_url_rule('/<{}:{}>/device'.format(self.ID_CONVERTER.value, self.ID_NAME),
                          view_func=_get_device_from_tag,
                          methods={'GET'})

    @option('--org',
            help='The name of an existing organization in the DB. '
                 'By default the organization operating this Devicehub.')
    @option('--provider',
            help='The Base URL of the provider. '
                 'By default set to the actual Devicehub.')
    @argument('ids', nargs=-1, required=True)
    def create_tags(self, ids: Tuple[str], org: str = None, provider: str = None):
        """Create TAGS and associates them to a specific PROVIDER."""
        tag_schema = TagS(only=('id', 'provider', 'org'))

        db.session.add_all(
            Tag(**tag_schema.load({'id': tag_id, 'provider': provider, 'org': org}))
            for tag_id in ids
        )
        db.session.commit()
