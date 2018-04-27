from ereuse_utils.test import JSON
from flask import Response
from werkzeug.exceptions import HTTPException

from teal.client import Client as TealClient


class Client(TealClient):
    def __init__(self, application, response_wrapper=None, use_cookies=False,
                 allow_subdomain_redirects=False):
        super().__init__(application, response_wrapper, use_cookies, allow_subdomain_redirects)

    def login(self, email: str, password: str):
        assert isinstance(email, str)
        assert isinstance(password, str)
        return self.post({'email': email, 'password': password}, '/users/login', status=200)


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

    def open(self, uri: str, res: str = None, status: int or HTTPException = 200, query: dict = {},
             accept=JSON, content_type=JSON, item=None, headers: dict = None, token: str = None,
             **kw) -> (dict or str, Response):
        return super().open(uri, res, status, query, accept, content_type, item, headers,
                            self.user['token'] if self.user else token, **kw)
