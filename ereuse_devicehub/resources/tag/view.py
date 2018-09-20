from flask import Response, current_app as app, request
from teal.marshmallow import ValidationError
from teal.resource import View

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.tag import Tag


class TagView(View):

    def post(self):
        """Creates a tag."""
        t = request.get_json()
        tag = Tag(**t)
        if tag.like_etag():
            raise CannotCreateETag(tag.id)
        db.session.add(tag)
        db.session.commit()
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


class TagNotLinked(ValidationError):
    def __init__(self, id):
        message = 'The tag {} is not linked to a device.'.format(id)
        super().__init__(message, field_names=['device'])


class CannotCreateETag(ValidationError):
    def __init__(self, id: str):
        message = 'Only sysadmin can create an eReuse.org Tag ({})'.format(id)
        super().__init__(message)
