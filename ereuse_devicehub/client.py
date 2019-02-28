from inspect import isclass
from typing import Dict, Iterable, Type, Union

from ereuse_utils.test import JSON, Res
from teal.client import Client as TealClient, Query, Status
from werkzeug.exceptions import HTTPException

from ereuse_devicehub.resources import models, schemas

ResourceLike = Union[Type[Union[models.Thing, schemas.Thing]], str]


class Client(TealClient):
    """A client suited for Devicehub main usage."""

    def __init__(self, application,
                 response_wrapper=None,
                 use_cookies=False,
                 allow_subdomain_redirects=False):
        super().__init__(application, response_wrapper, use_cookies, allow_subdomain_redirects)

    def open(self,
             uri: str,
             res: ResourceLike = None,
             status: Status = 200,
             query: Query = tuple(),
             accept=JSON,
             content_type=JSON,
             item=None,
             headers: dict = None,
             token: str = None,
             **kw) -> Res:
        if isclass(res) and issubclass(res, (models.Thing, schemas.Thing)):
            res = res.t
        return super().open(uri, res, status, query, accept, content_type, item, headers, token,
                            **kw)

    def get(self,
            uri: str = '',
            res: ResourceLike = None,
            query: Query = tuple(),
            status: Status = 200,
            item: Union[int, str] = None,
            accept: str = JSON,
            headers: dict = None,
            token: str = None,
            **kw) -> Res:
        return super().get(uri, res, query, status, item, accept, headers, token, **kw)

    def post(self,
             data: str or dict,
             uri: str = '',
             res: ResourceLike = None,
             query: Query = tuple(),
             status: Status = 201,
             content_type: str = JSON,
             accept: str = JSON,
             headers: dict = None,
             token: str = None,
             **kw) -> Res:
        return super().post(data, uri, res, query, status, content_type, accept, headers, token,
                            **kw)

    def patch(self,
              data: str or dict,
              uri: str = '',
              res: ResourceLike = None,
              query: Query = tuple(),
              item: Union[int, str] = None,
              status: Status = 200,
              content_type: str = JSON,
              accept: str = JSON,
              headers: dict = None,
              token: str = None,
              **kw) -> Res:
        return super().patch(data, uri, res, query, item, status, content_type, accept, token,
                             headers, **kw)

    def put(self,
            data: str or dict,
            uri: str = '',
            res: ResourceLike = None,
            query: Query = tuple(),
            item: Union[int, str] = None,
            status: Status = 201,
            content_type: str = JSON,
            accept: str = JSON,
            headers: dict = None,
            token: str = None,
            **kw) -> Res:
        return super().put(data, uri, res, query, item, status, content_type, accept, token,
                           headers, **kw)

    def delete(self,
               uri: str = '',
               res: ResourceLike = None,
               query: Query = tuple(),
               status: Status = 204,
               item: Union[int, str] = None,
               accept: str = JSON,
               headers: dict = None,
               token: str = None,
               **kw) -> Res:
        return super().delete(uri, res, query, status, item, accept, headers, token, **kw)

    def login(self, email: str, password: str):
        assert isinstance(email, str)
        assert isinstance(password, str)
        return self.post({'email': email, 'password': password}, '/users/login/', status=200)

    def get_many(self,
                 res: ResourceLike,
                 resources: Iterable[Union[dict, int]],
                 key: str = None,
                 **kw) -> Iterable[Union[Dict[str, object], str]]:
        """Like :meth:`.get` but with many resources."""
        return (
            self.get(res=res, item=r[key] if key else r, **kw)[0]
            for r in resources
        )


class UserClient(Client):
    """
    A client that identifies all of its requests with a specific user.

    It will automatically perform login on the first request.
    """

    def __init__(self, application,
                 email: str,
                 password: str,
                 response_wrapper=None,
                 use_cookies=False,
                 allow_subdomain_redirects=False):
        super().__init__(application, response_wrapper, use_cookies, allow_subdomain_redirects)
        self.email = email  # type: str
        self.password = password  # type: str
        self.user = None  # type: dict

    def open(self,
             uri: str,
             res: ResourceLike = None,
             status: int or HTTPException = 200,
             query: Query = tuple(),
             accept=JSON,
             content_type=JSON,
             item=None,
             headers: dict = None,
             token: str = None,
             **kw) -> Res:
        return super().open(uri, res, status, query, accept, content_type, item, headers,
                            self.user['token'] if self.user else token, **kw)

    # noinspection PyMethodOverriding
    def login(self):
        response = super().login(self.email, self.password)
        self.user = response[0]
        return response
