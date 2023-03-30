from contextlib import suppress
from typing import Dict, Tuple, Union

from flask import json
from flask.testing import FlaskClient
from werkzeug.wrappers import Response

from ereuse_devicehub.ereuse_utils.session import ANY, AUTH, BASIC, DevicehubClient, JSON, Query, Status

ANY = ANY
AUTH = AUTH
BASIC = BASIC

Res = Tuple[Union[Dict[str, object], str], Response]


class Client(FlaskClient):
    """
    A client for the REST servers of DeviceHub and WorkbenchServer.

    - JSON first. By default it sends and expects receiving JSON files.
    - Assert regular status responses, like 200 for GET.
    - Auto-parses a nested dictionary of URL query params to the
      URL version with nested properties to JSON.
    - Meaningful headers format: a dictionary of name-values.
    """

    def open(self,
             uri: str,
             status: Status = 200,
             query: Query = tuple(),
             accept=JSON,
             content_type=JSON,
             item=None,
             headers: dict = None,
             **kw) -> Res:
        """

        :param uri: The URI without basename and query.
        :param status: Assert the response for specified status. Set
                       None to avoid.
        :param query: The query of the URL in the form of
                      [(key1, value1), (key2, value2), (key1, value3)].
                      If value is a list or a dict, they will be
                      converted to JSON.
                      Please, see :class:`boltons.urlutils`.
                      QueryParamDict` for more info.
        :param accept: The Accept header. If 'application/json'
                       (default) then it will parse incoming JSON.
        :param item: The last part of the path. Useful to do something
                     like ``get('db/accounts', item='24')``. If you
                     use ``item``, you can't set a final backslash into
                     ``uri`` (or the parse will fail).
        :param headers: A dictionary of headers, where keys are header
                        names and values their values.
                        Ex: {'Accept', 'application/json'}.
        :param kw: Kwargs passed into parent ``open``.
        :return: A tuple with: 1. response data, as a string or JSON
                 depending of Accept, and 2. the Response object.
        """
        j_encoder = self.application.json_encoder
        headers = headers or {}
        headers['Accept'] = accept
        headers['Content-Type'] = content_type
        headers = [(k, v) for k, v in headers.items()]
        if 'data' in kw and content_type == JSON:
            kw['data'] = json.dumps(kw['data'], cls=j_encoder)
        if item:
            uri = DevicehubClient.parse_uri(uri, item)
        if query:
            uri = DevicehubClient.parse_query(uri, query)
        response = super().open(uri, headers=headers, **kw)
        if status:
            _status = getattr(status, 'code', status)
            assert response.status_code == _status, \
                'Expected status code {} but got {}. Returned data is:\n' \
                '{}'.format(_status, response.status_code, response.get_data().decode())

        data = response.get_data()
        with suppress(UnicodeDecodeError):
            data = data.decode()
        if accept == JSON:
            data = json.loads(data) if data else {}
        return data, response

    def get(self,
            uri: str,
            query: Query = tuple(),
            item: str = None,
            status: Status = 200,
            accept: str = JSON,
            headers: dict = None,
            **kw) -> Res:
        """
        Performs a GET.

        See the parameters in :meth:`ereuse_utils.test.Client.open`.
        Moreover:

        :param query: A dictionary of query params. If a parameter is a
                      dict or a list, it will be parsed to JSON, then
                      all params are encoded with ``urlencode``.
        :param kw: Kwargs passed into parent ``open``.
        """
        return super().get(uri, item=item, status=status, accept=accept, headers=headers,
                           query=query, **kw)

    def post(self,
             uri: str,
             data: str or dict,
             query: Query = tuple(),
             status: Status = 201,
             content_type: str = JSON,
             accept: str = JSON,
             headers: dict = None,
             **kw) -> Res:
        """
        Performs a POST.

        See the parameters in :meth:`ereuse_utils.test.Client.open`.
        """
        return super().post(uri, data=data, status=status, content_type=content_type,
                            accept=accept, headers=headers, query=query, **kw)

    def patch(self,
              uri: str,
              data: str or dict,
              query: Query = tuple(),
              status: Status = 200,
              content_type: str = JSON,
              item: str = None,
              accept: str = JSON,
              headers: dict = None,
              **kw) -> Res:
        """
        Performs a PATCH.

        See the parameters in :meth:`ereuse_utils.test.Client.open`.
        """
        return super().patch(uri, item=item, data=data, status=status, content_type=content_type,
                             accept=accept, headers=headers, query=query, **kw)

    def put(self,
            uri: str,
            data: str or dict,
            query: Query = tuple(),
            status: Status = 201,
            content_type: str = JSON,
            item: str = None,
            accept: str = JSON,
            headers: dict = None,
            **kw) -> Res:
        return super().put(uri, item=item, data=data, status=status, content_type=content_type,
                           accept=accept, headers=headers, query=query, **kw)

    def delete(self,
               uri: str,
               query: Query = tuple(),
               item: str = None,
               status: Status = 204,
               accept: str = JSON,
               headers: dict = None,
               **kw) -> Res:
        return super().delete(uri, query=query, item=item, status=status, accept=accept,
                              headers=headers, **kw)
