import teal.marshmallow
from ereuse_utils.test import ANY

from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.resources.documents import documents as docs
from ereuse_devicehub.resources.event import models as e
from tests.conftest import file


def test_erasure_certificate_public_one(user: UserClient, client: Client):
    """Public user can get certificate from one device as HTML or PDF."""
    s = file('erase-sectors.snapshot')
    snapshot, _ = user.post(s, res=e.Snapshot)

    doc, response = client.get(res=docs.DocumentDef.t,
                               item='erasures/{}'.format(snapshot['device']['id']),
                               accept=ANY)
    assert 'html' in response.content_type
    assert '<html' in doc
    assert '2018' in doc

    doc, response = client.get(res=docs.DocumentDef.t,
                               item='erasures/{}'.format(snapshot['device']['id']),
                               query=[('format', 'PDF')],
                               accept='application/pdf')
    assert 'application/pdf' == response.content_type

    erasure = next(e for e in snapshot['events'] if e['type'] == 'EraseSectors')

    doc, response = client.get(res=docs.DocumentDef.t,
                               item='erasures/{}'.format(erasure['id']),
                               accept=ANY)
    assert 'html' in response.content_type
    assert '<html' in doc
    assert '2018' in doc


def test_erasure_certificate_private_query(user: UserClient):
    """Logged-in user can get certificates using queries as HTML and
    PDF.
    """
    s = file('erase-sectors.snapshot')
    snapshot, response = user.post(s, res=e.Snapshot)

    doc, response = user.get(res=docs.DocumentDef.t,
                             item='erasures/',
                             query=[('filter', {'id': [snapshot['device']['id']]})],
                             accept=ANY)
    assert 'html' in response.content_type
    assert '<html' in doc
    assert '2018' in doc

    doc, response = user.get(res=docs.DocumentDef.t,
                             item='erasures/',
                             query=[
                                 ('filter', {'id': [snapshot['device']['id']]}),
                                 ('format', 'PDF')
                             ],
                             accept='application/pdf')
    assert 'application/pdf' == response.content_type


def test_erasure_certificate_wrong_id(client: Client):
    client.get(res=docs.DocumentDef.t, item='erasures/this-is-not-an-id',
               status=teal.marshmallow.ValidationError)
