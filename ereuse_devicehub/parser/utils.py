import datetime
import fcntl
import socket
import struct
from contextlib import contextmanager
from enum import Enum

from ereuse_utils import Dumpeable


class Severity(Enum):
    Info = 'Info'
    Error = 'Error'


def get_hw_addr(ifname):
    # http://stackoverflow.com/a/4789267/1538221
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', ifname[:15]))
    return ':'.join('%02x' % ord(char) for char in info[18:24])


class Measurable(Dumpeable):
    """A base class that allows measuring execution times."""

    def __init__(self) -> None:
        super().__init__()
        self.elapsed = None

    @contextmanager
    def measure(self):
        init = datetime.datetime.now(datetime.timezone.utc)
        yield
        self.elapsed = datetime.datetime.now(datetime.timezone.utc) - init
        try:
            assert self.elapsed.total_seconds() > 0
        except AssertionError:
            self.elapsed = datetime.timedelta(seconds=0)
