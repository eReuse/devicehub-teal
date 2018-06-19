from inspect import isclass
from typing import Any, Dict, Iterable, Tuple, Type, Union

from flask import Response
from werkzeug.exceptions import HTTPException

from ereuse_devicehub.resources import models, schemas
from ereuse_utils.test import JSON
from teal.client import Client as TealClient
from teal.marshmallow import ValidationError


class Client(TealClient):
    """A client suited for Devicehub main usage."""

    def __init__(self, application,
                 response_wrapper=None,
                 use_cookies=False,
                 allow_subdomain_redirects=False):
        super().__init__(application, response_wrapper, use_cookies, allow_subdomain_redirects)

    def open(self,
             uri: str,
             res: Union[str, Type[Union[models.Thing, schemas.Thing]]] = None,
             status: Union[int, Type[HTTPException], Type[ValidationError]] = 200,
             query: Iterable[Tuple[str, Any]] = tuple(),
             accept=JSON,
             content_type=JSON,
             item=None,
             headers: dict = None,
             token: str = None,
             **kw) -> Tuple[Union[Dict[str, object], str], Response]:
        if isclass(res) and issubclass(res, (models.Thing, schemas.Thing)):
            res = res.t
        return super().open(uri, res, status, query, accept, content_type, item, headers, token,
                            **kw)

    def get(self,
            uri: str = '',
            res: Union[Type[Union[models.Thing, schemas.Thing]], str] = None,
            query: Iterable[Tuple[str, Any]] = tuple(),
            status: Union[int, Type[HTTPException], Type[ValidationError]] = 200,
            item: Union[int, str] = None,
            accept: str = JSON,
            headers: dict = None,
            token: str = None,
            **kw) -> Tuple[Union[Dict[str, object], str], Response]:
        return super().get(uri, res, query, status, item, accept, headers, token, **kw)

    def post(self,
             data: str or dict,
             uri: str = '',
             res: Union[Type[Union[models.Thing, schemas.Thing]], str] = None,
             query: Iterable[Tuple[str, Any]] = tuple(),
             status: Union[int, Type[HTTPException], Type[ValidationError]] = 201,
             content_type: str = JSON,
             accept: str = JSON,
             headers: dict = None,
             token: str = None,
             **kw) -> Tuple[Union[Dict[str, object], str], Response]:
        return super().post(data, uri, res, query, status, content_type, accept, headers, token,
                            **kw)

    def login(self, email: str, password: str):
        assert isinstance(email, str)
        assert isinstance(password, str)
        return self.post({'email': email, 'password': password}, '/users/login', status=200)

    def get_many(self,
                 res: Union[Type[Union[models.Thing, schemas.Thing]], str],
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
             res: Union[str, Type[Union[models.Thing, schemas.Thing]]] = None,
             status: int or HTTPException = 200,
             query: Iterable[Tuple[str, Any]] = tuple(),
             accept=JSON,
             content_type=JSON,
             item=None,
             headers: dict = None,
             token: str = None,
             **kw) -> Tuple[Union[Dict[str, object], str], Response]:
        return super().open(uri, res, status, query, accept, content_type, item, headers,
                            self.user['token'] if self.user else token, **kw)
