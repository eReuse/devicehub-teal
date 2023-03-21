from typing import Any, Iterable, Tuple, Type, Union

from boltons.urlutils import URL
from ereuse_devicehub.ereuse_utils.test import JSON
from ereuse_devicehub.ereuse_utils.test import Client as EreuseUtilsClient
from ereuse_devicehub.ereuse_utils.test import Res
from werkzeug.exceptions import HTTPException

from ereuse_devicehub.teal.marshmallow import ValidationError

Status = Union[int, Type[HTTPException], Type[ValidationError]]
Query = Iterable[Tuple[str, Any]]


class Client(EreuseUtilsClient):
    """A REST interface to a Teal app."""

    def open(
        self,
        uri: str,
        res: str = None,
        status: Status = 200,
        query: Query = tuple(),
        accept=JSON,
        content_type=JSON,
        item=None,
        headers: dict = None,
        token: str = None,
        **kw,
    ) -> Res:
        headers = headers or {}
        if res:
            resource_url = self.application.resources[res].url_prefix + '/'
            uri = URL(uri).navigate(resource_url).to_text()
        if token:
            headers['Authorization'] = 'Basic {}'.format(token)
        res = super().open(
            uri, status, query, accept, content_type, item, headers, **kw
        )
        # ereuse-utils checks for status code
        # here we check for specific type
        # (when response: {'type': 'foobar', 'code': 422})
        _status = getattr(status, 'code', status)
        if not isinstance(status, int) and res[1].status_code == _status:
            assert (
                status.__name__ == res[0]['type']
            ), 'Expected exception {0} but it was {1}'.format(
                status.__name__, res[0]['type']
            )
        return res

    def get(
        self,
        uri: str = '',
        res: str = None,
        query: Query = tuple(),
        status: Status = 200,
        item=None,
        accept: str = JSON,
        headers: dict = None,
        token: str = None,
        **kw,
    ) -> Res:
        """
        Performs GET.

        :param uri: The uri where to GET from. This is optional, as you
                    can build the URI too through ``res`` and ``item``.
        :param res: The resource where to GET from, if any.
                    If this is set, the client will try to get the
                    url from the resource definition.
        :param query: The query params in a dict. This method
                      automatically converts the dict to URL params,
                      and if the dict had nested dictionaries, those
                      are converted to JSON.
        :param status: A status code or exception to assert.
        :param item: The id of a resource to GET from, if any.
        :param accept: The accept headers. By default
                       ``application/json``.
        :param headers: A dictionary of header name - header value.
        :param token: A token to add to an ``Authentication`` header.
        :return: A tuple containing 1. a dict (if content-type is JSON)
                 or a str with the data, and 2. the ``Response`` object.
        """
        kw['res'] = res
        kw['token'] = token
        return super().get(uri, query, item, status, accept, headers, **kw)

    def post(
        self,
        data: str or dict,
        uri: str = '',
        res: str = None,
        query: Query = tuple(),
        status: Status = 201,
        content_type: str = JSON,
        accept: str = JSON,
        headers: dict = None,
        token: str = None,
        **kw,
    ) -> Res:
        kw['res'] = res
        kw['token'] = token
        return super().post(
            uri, data, query, status, content_type, accept, headers, **kw
        )

    def patch(
        self,
        data: str or dict,
        uri: str = '',
        res: str = None,
        query: Query = tuple(),
        item=None,
        status: Status = 200,
        content_type: str = JSON,
        accept: str = JSON,
        token: str = None,
        headers: dict = None,
        **kw,
    ) -> Res:
        kw['res'] = res
        kw['token'] = token
        return super().patch(
            uri, data, query, status, content_type, item, accept, headers, **kw
        )

    def put(
        self,
        data: str or dict,
        uri: str = '',
        res: str = None,
        query: Query = tuple(),
        item=None,
        status: Status = 201,
        content_type: str = JSON,
        accept: str = JSON,
        token: str = None,
        headers: dict = None,
        **kw,
    ) -> Res:
        kw['res'] = res
        kw['token'] = token
        return super().put(
            uri, data, query, status, content_type, item, accept, headers, **kw
        )

    def delete(
        self,
        uri: str = '',
        res: str = None,
        query: Query = tuple(),
        status: Status = 204,
        item=None,
        accept: str = JSON,
        headers: dict = None,
        token: str = None,
        **kw,
    ) -> Res:
        kw['res'] = res
        kw['token'] = token
        return super().delete(uri, query, item, status, accept, headers, **kw)

    def post_get(
        self,
        res: str,
        data: str or dict,
        query: Query = tuple(),
        status: Status = 200,
        content_type: str = JSON,
        accept: str = JSON,
        headers: dict = None,
        key='id',
        token: str = None,
        **kw,
    ) -> Res:
        """Performs post and then gets the resource through its key."""
        r, _ = self.post(
            '', data, res, query, status, content_type, accept, token, headers, **kw
        )
        return self.get(res=res, item=r[key])
