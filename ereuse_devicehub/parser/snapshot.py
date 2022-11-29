from datetime import datetime, timezone

from ereuse_workbench.computer import Computer, DataStorage
from ereuse_workbench.utils import Dumpeable


class Snapshot(Dumpeable):
    """
    Generates the Snapshot report for Devicehub by obtaining the
    data from the computer, performing benchmarks and tests...

    After instantiating the class, run :meth:`.computer` before any
    other method.
    """

    def __init__(self, uuid, software, version, lshw, hwinfo):
        self.type = 'Snapshot'
        self.uuid = uuid
        self.software = software
        self.version = version
        self.lshw = lshw
        self.hwinfo = hwinfo
        self.endTime = datetime.now(timezone.utc)
        self.closed = False
        self.elapsed = None
        self.device = None
        self.components = None
        self._storages = None

    def computer(self):
        """Retrieves information about the computer and components."""
        self.device, self.components = Computer.run(self.lshw, self.hwinfo)
        self._storages = tuple(c for c in self.components if isinstance(c, DataStorage))

    def close(self):
        """Closes the Snapshot"""
        self.closed = True
