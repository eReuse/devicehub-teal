import pytest
from pytest import raises
from sqlalchemy.exc import IntegrityError

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.models import Computer
from ereuse_devicehub.resources.tag import Tag
from ereuse_devicehub.resources.tag.view import CannotCreateETag, TagNotLinked
from ereuse_devicehub.resources.user import Organization
from teal.db import MultipleResourcesFound, ResourceNotFound
from teal.marshmallow import ValidationError


@pytest.mark.usefixtures('app_context')
def test_create_tag():
    """Creates a tag specifying a custom organization."""
    org = Organization(name='Bar', tax_id='BarTax')
    tag = Tag(id='bar-1', org=org)
    db.session.add(tag)
    db.session.commit()


@pytest.mark.usefixtures('app_context')
def test_create_tag_default_org():
    """Creates a tag using the default organization."""
    tag = Tag(id='foo-1')
    assert not tag.org_id, 'org-id is set as default value so it should only load on flush'
    # We don't want the organization to load, or it would make this
    # object, from transient to new (added to session)
    assert 'org' not in vars(tag), 'Organization should not have been loaded'
    db.session.add(tag)
    db.session.commit()
    assert tag.org.name == 'FooOrg'  # as defined in the settings


@pytest.mark.usefixtures('app_context')
def test_create_tag_no_slash():
    """Checks that no tags can be created that contain a slash."""
    with raises(ValidationError):
        Tag(id='/')


@pytest.mark.usefixtures('app_context')
def test_create_two_same_tags():
    """Ensures there cannot be two tags with the same ID and organization."""
    db.session.add(Tag(id='foo-bar'))
    db.session.add(Tag(id='foo-bar'))
    with raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    # And it works if tags are in different organizations
    db.session.add(Tag(id='foo-bar'))
    org2 = Organization(name='org 2', tax_id='tax id org 2')
    db.session.add(Tag(id='foo-bar', org=org2))
    db.session.commit()


def test_tag_post(app: Devicehub, user: UserClient):
    """Checks the POST method of creating a tag."""
    user.post(res=Tag, query=[('ids', 'foo')], data={})
    with app.app_context():
        assert Tag.query.filter_by(id='foo').one()


def test_tag_post_etag(user: UserClient):
    """
    Ensures users cannot create eReuse.org tags through POST;
    only terminal.
    """
    user.post(res=Tag, query=[('ids', 'FO-123456')], data={}, status=CannotCreateETag)
    # Although similar, these are not eTags and should pass
    user.post(res=Tag, query=[
        ('ids', 'FO-0123-45'),
        ('ids', 'FOO012345678910'),
        ('ids', 'FO'),
        ('ids', 'FO-'),
        ('ids', 'FO-123'),
        ('ids', 'FOO-123456')
    ], data={})


def test_tag_get_device_from_tag_endpoint(app: Devicehub, user: UserClient):
    """Checks getting a linked device from a tag endpoint"""
    with app.app_context():
        # Create a pc with a tag
        tag = Tag(id='foo-bar')
        pc = Computer(serial_number='sn1')
        pc.tags.add(tag)
        db.session.add(pc)
        db.session.commit()
    computer, _ = user.get(res=Tag, item='foo-bar/device')
    assert computer['serialNumber'] == 'sn1'


def test_tag_get_device_from_tag_endpoint_no_linked(app: Devicehub, user: UserClient):
    """As above, but when the tag is not linked."""
    with app.app_context():
        db.session.add(Tag(id='foo-bar'))
        db.session.commit()
    user.get(res=Tag, item='foo-bar/device', status=TagNotLinked)


def test_tag_get_device_from_tag_endpoint_no_tag(user: UserClient):
    """As above, but when there is no tag with such ID."""
    user.get(res=Tag, item='foo-bar/device', status=ResourceNotFound)


def test_tag_get_device_from_tag_endpoint_multiple_tags(app: Devicehub, user: UserClient):
    """
    As above, but when there are two tags with the same ID, the
    system should not return any of both (to be deterministic) so
    it should raise an exception.
    """
    with app.app_context():
        db.session.add(Tag(id='foo-bar'))
        org2 = Organization(name='org 2', tax_id='tax id org 2')
        db.session.add(Tag(id='foo-bar', org=org2))
        db.session.commit()
    user.get(res=Tag, item='foo-bar/device', status=MultipleResourcesFound)
