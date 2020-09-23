import pathlib

import pytest
import requests_mock
from boltons.urlutils import URL
from ereuse_utils.session import DevicehubClient
from pytest import raises
from teal.db import MultipleResourcesFound, ResourceNotFound, UniqueViolation, DBError
from teal.marshmallow import ValidationError

from ereuse_devicehub.client import UserClient
from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.action.models import Snapshot
from ereuse_devicehub.resources.agent.models import Organization
from ereuse_devicehub.resources.device.models import Desktop, Device
from ereuse_devicehub.resources.enums import ComputerChassis
from ereuse_devicehub.resources.tag import Tag
from ereuse_devicehub.resources.tag.view import CannotCreateETag, LinkedToAnotherDevice, \
    TagNotLinked
from tests import conftest
from tests.conftest import file


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_create_tag(user: UserClient):
    """Creates a tag specifying a custom organization."""
    org = Organization(name='bar', tax_id='bartax')
    tag = Tag(id='bar-1', org=org, provider=URL('http://foo.bar'), owner_id=user.user['id'])
    db.session.add(tag)
    db.session.commit()
    tag = Tag.query.one()
    assert tag.id == 'bar-1'
    assert tag.provider == URL('http://foo.bar')


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_create_tag_default_org(user: UserClient):
    """Creates a tag using the default organization."""
    tag = Tag(id='foo-1', owner_id=user.user['id'])
    assert not tag.org_id, 'org-id is set as default value so it should only load on flush'
    # We don't want the organization to load, or it would make this
    # object, from transient to new (added to session)
    assert 'org' not in vars(tag), 'Organization should not have been loaded'
    db.session.add(tag)
    db.session.commit()
    assert tag.org.name == 'FooOrg'  # as defined in the settings


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_create_tag_no_slash():
    """Checks that no tags can be created that contain a slash."""
    with raises(ValidationError):
        Tag('/')

    with raises(ValidationError):
        Tag('bar', secondary='/')


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_create_two_same_tags(user: UserClient):
    """Ensures there cannot be two tags with the same ID and organization."""

    db.session.add(Tag(id='foo-bar', owner_id=user.user['id']))
    db.session.add(Tag(id='foo-bar', owner_id=user.user['id']))

    with raises(DBError):
        db.session.commit()
    db.session.rollback()
    # And it works if tags are in different organizations
    db.session.add(Tag(id='foo-bar', owner_id=user.user['id']))
    org2 = Organization(name='org 2', tax_id='tax id org 2')
    db.session.add(Tag(id='foo-bar', org=org2, owner_id=user.user['id']))
    db.session.commit()


@pytest.mark.mvp
def test_tag_post(app: Devicehub, user: UserClient):
    """Checks the POST method of creating a tag."""
    user.post({'id': 'foo'}, res=Tag)
    with app.app_context():
        assert Tag.query.filter_by(id='foo').one()


@pytest.mark.mvp
def test_tag_post_etag(user: UserClient):
    """Ensures users cannot create eReuse.org tags through POST;
    only terminal.
    """
    user.post({'id': 'FO-123456'}, res=Tag, status=CannotCreateETag)
    # Although similar, these are not eTags and should pass
    user.post({'id': 'FO-0123-45'}, res=Tag)
    user.post({'id': 'FOO012345678910'}, res=Tag)
    user.post({'id': 'FO'}, res=Tag)
    user.post({'id': 'FO-'}, res=Tag)
    user.post({'id': 'FO-123'}, res=Tag)
    user.post({'id': 'FOO-123456'}, res=Tag)


@pytest.mark.mvp
def test_tag_get_device_from_tag_endpoint(app: Devicehub, user: UserClient):
    """Checks getting a linked device from a tag endpoint"""
    with app.app_context():
        # Create a pc with a tag
        tag = Tag(id='foo-bar', owner_id=user.user['id'])
        pc = Desktop(serial_number='sn1', chassis=ComputerChassis.Tower, owner_id=user.user['id'])
        pc.tags.add(tag)
        db.session.add(pc)
        db.session.commit()
    computer, _ = user.get(res=Tag, item='foo-bar/device')
    assert computer['serialNumber'] == 'sn1'


@pytest.mark.mvp
def test_tag_get_device_from_tag_endpoint_no_linked(app: Devicehub, user: UserClient):
    """As above, but when the tag is not linked."""
    with app.app_context():
        db.session.add(Tag(id='foo-bar', owner_id=user.user['id']))
        db.session.commit()
    user.get(res=Tag, item='foo-bar/device', status=TagNotLinked)


@pytest.mark.mvp
def test_tag_get_device_from_tag_endpoint_no_tag(user: UserClient):
    """As above, but when there is no tag with such ID."""
    user.get(res=Tag, item='foo-bar/device', status=ResourceNotFound)


@pytest.mark.mvp
def test_tag_get_device_from_tag_endpoint_multiple_tags(app: Devicehub, user: UserClient):
    """As above, but when there are two tags with the same ID, the
    system should not return any of both (to be deterministic) so
    it should raise an exception.
    """
    with app.app_context():
        db.session.add(Tag(id='foo-bar', owner_id=user.user['id']))
        org2 = Organization(name='org 2', tax_id='tax id org 2')
        db.session.add(Tag(id='foo-bar', org=org2, owner_id=user.user['id']))
        db.session.commit()
    user.get(res=Tag, item='foo-bar/device', status=MultipleResourcesFound)


@pytest.mark.mvp
def test_tag_create_tags_cli(app: Devicehub, user: UserClient):
    """Checks creating tags with the CLI endpoint."""
    owner_id = user.user['id']
    runner = app.test_cli_runner()
    runner.invoke('tag', 'add', 'id1', '-u', owner_id)
    with app.app_context():
        tag = Tag.query.one()  # type: Tag
        assert tag.id == 'id1'
        assert tag.org.id == Organization.get_default_org_id()


@pytest.mark.mvp
def test_tag_create_etags_cli(app: Devicehub, user: UserClient):
    """Creates an eTag through the CLI."""
    # todo what happens to organization?
    owner_id = user.user['id']
    runner = app.test_cli_runner()
    args = ('tag', 'add', '-p', 'https://t.ereuse.org', '-s', 'foo', 'DT-BARBAR', '-u', owner_id)
    runner.invoke(*args)
    with app.app_context():
        tag = Tag.query.one()  # type: Tag
        assert tag.id == 'dt-barbar'
        assert tag.secondary == 'foo'
        assert tag.provider == URL('https://t.ereuse.org')


@pytest.mark.mvp
def test_tag_manual_link_search(app: Devicehub, user: UserClient):
    """Tests linking manually a tag through PUT /tags/<id>/device/<id>

    Checks search has the term.
    """
    with app.app_context():
        db.session.add(Tag('foo-bar', secondary='foo-sec', owner_id=user.user['id']))
        desktop = Desktop(serial_number='foo', chassis=ComputerChassis.AllInOne, owner_id=user.user['id'])
        db.session.add(desktop)
        db.session.commit()
        desktop_id = desktop.id
    user.put({}, res=Tag, item='foo-bar/device/{}'.format(desktop_id), status=204)
    device, _ = user.get(res=Device, item=1)
    assert device['tags'][0]['id'] == 'foo-bar'

    # Device already linked
    # Just returns an OK to conform to PUT as anything changes

    user.put({}, res=Tag, item='foo-sec/device/{}'.format(desktop_id), status=204)

    # Secondary IDs are case insensitive
    user.put({}, res=Tag, item='FOO-BAR/device/{}'.format(desktop_id), status=204)
    user.put({}, res=Tag, item='FOO-SEC/device/{}'.format(desktop_id), status=204)

    # cannot link to another device when already linked
    user.put({}, res=Tag, item='foo-bar/device/99', status=LinkedToAnotherDevice)

    i, _ = user.get(res=Device, query=[('search', 'foo-bar')])
    assert i['items']
    i, _ = user.get(res=Device, query=[('search', 'foo-sec')])
    assert i['items']
    i, _ = user.get(res=Device, query=[('search', 'foo')])
    assert i['items']


@pytest.mark.mvp
@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_tag_secondary_workbench_link_find(user: UserClient):
    """Creates and consumes tags with a secondary id, linking them
    through Workbench to a device
    and getting them through search."""
    t = Tag('foo', secondary='bar', owner_id=user.user['id'])
    db.session.add(t)
    db.session.flush()
    assert Tag.from_an_id('bar').one() == t
    assert Tag.from_an_id('foo').one() == t
    with pytest.raises(ResourceNotFound):
        Tag.from_an_id('nope').one()

    s = file('basic.snapshot')
    s['device']['tags'] = [{'id': 'foo', 'secondary': 'bar', 'type': 'Tag'}]
    snapshot, _ = user.post(s, res=Snapshot)
    device, _ = user.get(res=Device, item=snapshot['device']['id'])
    assert device['tags'][0]['id'] == 'foo'
    assert device['tags'][0]['secondary'] == 'bar'

    r, _ = user.get(res=Device, query=[('search', 'foo'), ('filter', {'type': ['Computer']})])
    assert len(r['items']) == 1
    r, _ = user.get(res=Device, query=[('search', 'bar'), ('filter', {'type': ['Computer']})])
    assert len(r['items']) == 1


@pytest.mark.mvp
def test_tag_create_tags_cli_csv(app: Devicehub, user: UserClient):
    """Checks creating tags with the CLI endpoint using a CSV."""
    owner_id = user.user['id']
    csv = pathlib.Path(__file__).parent / 'files' / 'tags-cli.csv'
    runner = app.test_cli_runner()
    runner.invoke('tag', 'add-csv', str(csv), '-u', owner_id)
    with app.app_context():
        t1 = Tag.from_an_id('id1').one()
        t2 = Tag.from_an_id('sec1').one()
        assert t1 == t2


def test_tag_multiple_secondary_org(user: UserClient):
    """Ensures two secondary ids cannot be part of the same Org."""
    user.post({'id': 'foo', 'secondary': 'bar'}, res=Tag)
    user.post({'id': 'foo1', 'secondary': 'bar'}, res=Tag, status=UniqueViolation)


@pytest.mark.mvp
def test_create_num_regular_tags(user: UserClient, requests_mock: requests_mock.mocker.Mocker):
    """Create regular tags. This is done using a tag provider that
    returns IDs. These tags are printable.
    """
    requests_mock.post('https://example.com/',
                       # request
                       request_headers={
                           'Authorization': 'Basic {}'.format(DevicehubClient.encode_token(
                               '52dacef0-6bcb-4919-bfed-f10d2c96ecee'))
                       },
                       # response
                       json=['tag1id', 'tag2id'],
                       status_code=201)
    data, _ = user.post({}, res=Tag, query=[('num', 2)])
    assert data['items'][0]['id'] == 'tag1id'
    assert data['items'][0]['printable'], 'Tags made this way are printable'
    assert data['items'][1]['id'] == 'tag2id'
    assert data['items'][1]['printable']


@pytest.mark.mvp
def test_get_tags_endpoint(user: UserClient, app: Devicehub,
                           requests_mock: requests_mock.mocker.Mocker):
    """Performs GET /tags after creating 3 tags, 2 printable and one
    not. Only the printable ones are returned.
    """
    # Prepare test
    with app.app_context():
        org = Organization(name='bar', tax_id='bartax')
        tag = Tag(id='bar-1', org=org, provider=URL('http://foo.bar'), owner_id=user.user['id'])
        db.session.add(tag)
        db.session.commit()
        assert not tag.printable

    requests_mock.post('https://example.com/',
                       # request
                       request_headers={
                           'Authorization': 'Basic {}'.format(DevicehubClient.encode_token(
                               '52dacef0-6bcb-4919-bfed-f10d2c96ecee'))
                       },
                       # response
                       json=['tag1id', 'tag2id'],
                       status_code=201)
    user.post({}, res=Tag, query=[('num', 2)])

    # Test itself
    data, _ = user.get(res=Tag)
    assert len(data['items']) == 2, 'Only 2 tags are printable, thus retreived'
    # Order is created descending
    assert data['items'][0]['id'] == 'tag2id'
    assert data['items'][0]['printable']
    assert data['items'][1]['id'] == 'tag1id'
    assert data['items'][1]['printable'], 'Tags made this way are printable'
