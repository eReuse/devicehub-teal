"""
An exemplifying Apache python WSGI to a Devicehub app with a dispatcher.
"""
from ereuse_devicehub.dispatchers import PathDispatcher

application = PathDispatcher()
