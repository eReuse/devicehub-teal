from flask import Response, current_app as app, request
from marshmallow.fields import List, String, URL
from webargs.flaskparser import parser

from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.tag import Tag
from teal.marshmallow import ValidationError
from teal.resource import View, Schema


class TagView(View):
    class PostArgs(Schema):
        ids = List(String(), required=True, description='A list of tags identifiers.')
        org = String(description='The name of an existing organization in the DB. '
                                 'If not set, the default organization is used.')
        provider = URL(description='The Base URL of the provider. By default is this Devicehub.')

    post_args = PostArgs()

    def post(self):
        """
        Creates tags.

        ---
        parameters:
          - name: tags
            in: path
            description: Number of tags to create.
        """
        args = parser.parse(self.post_args, request, locations={'querystring'})
        # Ensure user is not POSTing an eReuse.org tag
        # For now only allow them to be created through command-line
        for id in args['ids']:
            try:
                provider, _id = id.split('-')
            except ValueError:
                pass
            else:
                if len(provider) == 2 and 5 <= len(_id) <= 10:
                    raise CannotCreateETag(id)
        self.resource_def.create_tags(**args)
        return Response(status=201)


def get_device_from_tag(id: str):
    """
    Gets the device by passing a tag id.

    Example: /tags/23/device.

    :raise MultipleTagsPerId: More than one tag per Id. Please, use
           the /tags/<organization>/<id>/device URL to disambiguate.
    """
    # todo this could be more efficient by Device.query... join with tag
    device = Tag.query.filter_by(id=id).one().device
    if device is None:
        raise TagNotLinked(id)
    return app.resources[Device.t].schema.jsonify(device)


class CannotCreateETag(ValidationError):
    def __init__(self, id: str):
        message = 'Only sysadmin can create an eReuse.org Tag ({})'.format(id)
        super().__init__(message)


class TagNotLinked(ValidationError):
    def __init__(self, id):
        message = 'The tag {} is not linked to a device.'.format(id)
        super().__init__(message, field_names=['device'])
