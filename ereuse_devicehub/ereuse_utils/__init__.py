import enum
import ipaddress
import json
import locale
from collections import Iterable
from datetime import datetime, timedelta
from decimal import Decimal
from distutils.version import StrictVersion
from functools import wraps
from typing import Generator, Union
from uuid import UUID


class JSONEncoder(json.JSONEncoder):
    """An overloaded JSON Encoder with extra type support."""

    def default(self, obj):
        if isinstance(obj, enum.Enum):
            return obj.name
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return round(obj.total_seconds())
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, StrictVersion):
            return str(obj)
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, Dumpeable):
            return obj.dump()
        elif isinstance(obj, ipaddress._BaseAddress):
            return str(obj)
        # Instead of failing, return the string representation by default
        return str(obj)


class Dumpeable:
    """Dumps dictionaries and jsons for Devicehub.

    A base class to allow subclasses to generate dictionaries
    and json suitable for sending to a Devicehub, i.e. preventing
    private and  constants to be in the JSON and camelCases field names.
    """

    ENCODER = JSONEncoder

    def dump(self):
        """
        Creates a dictionary consisting of the
        non-private fields of this instance with camelCase field names.
        """
        import inflection

        return {
            inflection.camelize(name, uppercase_first_letter=False): getattr(self, name)
            for name in self._field_names()
            if not name.startswith('_') and not name[0].isupper()
        }

    def _field_names(self):
        """An iterable of the names to dump."""
        # Feel free to override this
        return vars(self).keys()

    def to_json(self):
        """
        Creates a JSON representation of the non-private fields of
        this class.
        """
        return json.dumps(self, cls=self.ENCODER, indent=2)


class DumpeableModel(Dumpeable):
    """A dumpeable for SQLAlchemy models.

    Note that this does not avoid recursive relations.
    """

    def _field_names(self):
        from sqlalchemy import inspect

        return (a.key for a in inspect(self).attrs)


def ensure_utf8(app_name_to_show_on_error: str):
    """
    Python3 uses by default the system set, but it expects it to be
    ‘utf-8’ to work correctly.
    This can generate problems in reading and writing files and in
    ``.decode()`` method.

    An example how to 'fix' it::

        echo 'export LC_CTYPE=en_US.UTF-8' > .bash_profile
        echo 'export LC_ALL=en_US.UTF-8' > .bash_profile
    """
    encoding = locale.getpreferredencoding()
    if encoding.lower() != 'utf-8':
        raise OSError(
            '{} works only in UTF-8, but yours is set at {}'
            ''.format(app_name_to_show_on_error, encoding)
        )


def now() -> datetime:
    """
    Returns a compatible 'now' with DeviceHub's API,
    this is as UTC and without microseconds.
    """
    return datetime.utcnow().replace(microsecond=0)


def flatten_mixed(values: Iterable) -> Generator:
    """
    Flatten a list containing lists and other elements. This is not deep.

    >>> list(flatten_mixed([1, 2, [3, 4]]))
    [1, 2, 3, 4]
    """
    for x in values:
        if isinstance(x, list):
            for y in x:
                yield y
        else:
            yield x


def if_none_return_none(f):
    """If the first value is None return None, otherwise execute f."""

    @wraps(f)
    def wrapper(self, value, *args, **kwargs):
        if value is None:
            return None
        return f(self, value, *args, **kwargs)

    return wrapper


def local_ip(
    dest='109.69.8.152',
) -> Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
    """Gets the local IP of the interface that has access to the
    Internet.

    This is a reliable way to test if a device has an active
    connection to the Internet.

    This method works by connecting, by default,
    to the IP of ereuse01.ereuse.org.

    >>> local_ip()

    :raise OSError: The device cannot connect to the Internet.
    """
    import socket, ipaddress

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((dest, 80))
    ip = s.getsockname()[0]
    s.close()
    return ipaddress.ip_address(ip)


def version(package_name: str) -> StrictVersion:
    """Returns the version of a package name installed with pip."""
    # From https://stackoverflow.com/a/2073599
    import pkg_resources

    return StrictVersion(pkg_resources.require(package_name)[0].version)
