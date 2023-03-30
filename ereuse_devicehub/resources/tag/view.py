from flask import Response
from flask import current_app as app
from flask import g, redirect, request
from flask_sqlalchemy import Pagination

from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.query import things_response
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.tag import Tag
from ereuse_devicehub.resources.utils import hashcode
from ereuse_devicehub.teal.marshmallow import ValidationError
from ereuse_devicehub.teal.resource import View, url_for_resource


class TagView(View):
    def one(self, code):
        """Gets the device from the named tag, /tags/namedtag."""
        internal_id = hashcode.decode(code.upper()) or -1
        tag = Tag.query.filter_by(internal_id=internal_id).one()  # type: Tag
        if not tag.device:
            raise TagNotLinked(tag.id)
        return redirect(location=url_for_resource(Device, tag.device.devicehub_id))

    @auth.Auth.requires_auth
    def post(self):
        """Creates a tag."""
        num = request.args.get('num', type=int)
        if num:
            # create unnamed tag
            res = self._create_many_regular_tags(num)
        else:
            # create named tag
            res = self._post_one()
        return res

    @auth.Auth.requires_auth
    def find(self, args: dict):
        tags = (
            Tag.query.filter(Tag.is_printable_q())
            .filter_by(owner=g.user)
            .order_by(Tag.created.desc())
            .paginate(per_page=200)
        )  # type: Pagination
        return things_response(
            self.schema.dump(tags.items, many=True, nested=0),
            tags.page,
            tags.per_page,
            tags.total,
            tags.prev_num,
            tags.next_num,
        )

    def _create_many_regular_tags(self, num: int):
        tags_id, _ = g.tag_provider.post('/', {}, query=[('num', num)])
        tags = [Tag(id=tag_id, provider=g.inventory.tag_provider) for tag_id in tags_id]
        db.session.add_all(tags)
        db.session().final_flush()
        response = things_response(
            self.schema.dump(tags, many=True, nested=1), code=201
        )
        db.session.commit()
        return response

    def _post_one(self):
        t = request.get_json()
        tag = Tag(**t)
        if tag.like_etag():
            raise CannotCreateETag(tag.id)
        db.session.add(tag)
        db.session().final_flush()
        db.session.commit()
        return Response(status=201)

    @auth.Auth.requires_auth
    def delete(self, id):
        tag = Tag.from_an_id(id).filter_by(owner=g.user).one()
        tag.delete()
        db.session().final_flush()
        db.session.commit()
        return Response(status=204)


class TagDeviceView(View):
    """Endpoints to work with the device of the tag; /tags/23/device."""

    def one(self, id):
        """Gets the device from the tag."""
        if request.authorization:
            return self.one_authorization(id)

        tag = Tag.from_an_id(id).one()  # type: Tag
        if not tag.device:
            raise TagNotLinked(tag.id)
        if not request.authorization:
            return redirect(location=url_for_resource(Device, tag.device.devicehub_id))
        return app.resources[Device.t].schema.jsonify(tag.device.devicehub_id)

    @auth.Auth.requires_auth
    def one_authorization(self, id):
        tag = Tag.from_an_id(id).filter_by(owner=g.user).one()  # type: Tag
        if not tag.device:
            raise TagNotLinked(tag.id)
        return app.resources[Device.t].schema.jsonify(tag.device)

    @auth.Auth.requires_auth
    def put(self, tag_id: str, device_id: int):
        """Links an existing tag with a device."""
        device_id = int(device_id)
        tag = Tag.from_an_id(tag_id).filter_by(owner=g.user).one()  # type: Tag
        if tag.device_id:
            if tag.device_id == device_id:
                return Response(status=204)
            else:
                raise LinkedToAnotherDevice(tag.device_id)
        else:
            # Check if this device exist for this owner
            Device.query.filter_by(owner=g.user).filter_by(id=device_id).one()
            tag.device_id = device_id

        db.session().final_flush()
        db.session.commit()
        return Response(status=204)

    @auth.Auth.requires_auth
    def delete(self, tag_id: str, device_id: str):
        tag = Tag.from_an_id(tag_id).filter_by(owner=g.user).one()  # type: Tag
        device = Device.query.filter_by(owner=g.user).filter_by(id=device_id).one()
        if tag.provider:
            # if is an unamed tag not do nothing
            return Response(status=204)

        if tag.device == device:
            tag.device_id = None
            db.session().final_flush()
            db.session.commit()
        return Response(status=204)


def get_device_from_tag(id: str):
    """Gets the device by passing a tag id.

    Example: /tags/23/device.

    :raise MultipleTagsPerId: More than one tag per Id. Please, use
           the /tags/<organization>/<id>/device URL to disambiguate.
    """
    # todo this could be more efficient by Device.query... join with tag
    device = Tag.query.filter_by(id=id).one().device
    if not request.authorization:
        return redirect(location=url_for_resource(Device, device.devicehub_id))
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


class LinkedToAnotherDevice(ValidationError):
    def __init__(self, device_id: int):
        message = 'The tag is already linked to device {}'.format(device_id)
        super().__init__(message)
